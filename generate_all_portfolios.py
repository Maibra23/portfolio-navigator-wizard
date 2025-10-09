#!/usr/bin/env python3
"""
One-Time Portfolio Generation System
Generates all portfolios for all risk profiles and updates PORTFOLIOS_IN_REDIS.md automatically
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main execution function"""
    print("🚀 Starting Portfolio Generation System")
    print("=" * 60)
    
    try:
        # Import services
        from utils.redis_first_data_service import RedisFirstDataService
        from utils.redis_portfolio_manager import RedisPortfolioManager
        from utils.enhanced_portfolio_generator import EnhancedPortfolioGenerator
        from utils.port_analytics import PortfolioAnalytics
        from utils.portfolio_auto_regeneration_service import PortfolioAutoRegenerationService
        
        # Initialize services
        print("📊 Initializing services...")
        rds = RedisFirstDataService()
        portfolio_analytics = PortfolioAnalytics()
        redis_manager = RedisPortfolioManager(rds.redis_client)
        enhanced_generator = EnhancedPortfolioGenerator(rds, portfolio_analytics)
        auto_regen_service = PortfolioAutoRegenerationService(rds, enhanced_generator, redis_manager)
        
        # Check Redis connection
        if not rds.redis_client:
            raise Exception("Redis connection failed")
        
        print("✅ Services initialized successfully")
        
        # Risk profiles to generate
        risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']

        # Optional mode: sanitize-only (replace portfolios with NaN/negative expectedReturn)
        if '--sanitize-invalid' in sys.argv or os.environ.get('SANITIZE_INVALID', '') == '1':
            return sanitize_invalid_portfolios(rds, redis_manager, enhanced_generator, portfolio_analytics, risk_profiles)
        
        # Clear existing portfolios
        print("\n🧹 Clearing existing portfolios...")
        for risk_profile in risk_profiles:
            try:
                redis_manager.clear_portfolio_bucket(risk_profile)
                print(f"  ✅ Cleared {risk_profile}")
            except Exception as e:
                print(f"  ⚠️ Error clearing {risk_profile}: {e}")
        
        # Generate portfolios for all risk profiles
        print("\n🎯 Generating portfolios for all risk profiles...")
        generation_results = {}
        total_start_time = time.time()
        
        for i, risk_profile in enumerate(risk_profiles, 1):
            print(f"\n📈 [{i}/{len(risk_profiles)}] Generating {risk_profile} portfolios...")
            start_time = time.time()
            
            try:
                # Generate 12 portfolios for this risk profile
                portfolios = enhanced_generator.generate_portfolio_bucket(risk_profile, use_parallel=True)
                
                if not portfolios or len(portfolios) < 12:
                    raise Exception(f"Generated only {len(portfolios) if portfolios else 0} portfolios, expected 12")
                
                # Store portfolios in Redis
                storage_success = redis_manager.store_portfolio_bucket(risk_profile, portfolios)
                
                if not storage_success:
                    raise Exception("Failed to store portfolios in Redis")
                
                generation_time = time.time() - start_time
                generation_results[risk_profile] = {
                    'success': True,
                    'portfolio_count': len(portfolios),
                    'generation_time': round(generation_time, 2),
                    'avg_time_per_portfolio': round(generation_time / len(portfolios), 3)
                }
                
                print(f"  ✅ Generated {len(portfolios)} portfolios in {generation_time:.2f}s")
                
            except Exception as e:
                generation_time = time.time() - start_time
                generation_results[risk_profile] = {
                    'success': False,
                    'error': str(e),
                    'generation_time': round(generation_time, 2)
                }
                print(f"  ❌ Failed: {e}")
        
        total_generation_time = time.time() - total_start_time
        
        # Generate summary report
        print("\n📊 Generation Summary:")
        print("=" * 40)
        successful_profiles = [rp for rp, result in generation_results.items() if result['success']]
        failed_profiles = [rp for rp, result in generation_results.items() if not result['success']]
        
        print(f"✅ Successful: {len(successful_profiles)}/{len(risk_profiles)} profiles")
        print(f"❌ Failed: {len(failed_profiles)} profiles")
        print(f"⏱️ Total time: {total_generation_time:.2f}s")
        
        if successful_profiles:
            total_portfolios = sum(result['portfolio_count'] for result in generation_results.values() if result['success'])
            print(f"📈 Total portfolios generated: {total_portfolios}")
            avg_time = sum(result['generation_time'] for result in generation_results.values() if result['success']) / len(successful_profiles)
            print(f"📊 Average time per profile: {avg_time:.2f}s")
        
        if failed_profiles:
            print(f"\n❌ Failed profiles: {', '.join(failed_profiles)}")
            for profile in failed_profiles:
                print(f"  - {profile}: {generation_results[profile]['error']}")
        
        # Update PORTFOLIOS_IN_REDIS.md
        print("\n📝 Updating PORTFOLIOS_IN_REDIS.md...")
        try:
            update_portfolios_markdown()
            print("  ✅ PORTFOLIOS_IN_REDIS.md updated successfully")
        except Exception as e:
            print(f"  ❌ Failed to update markdown: {e}")
        
        # Save generation report
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_generation_time': total_generation_time,
            'generation_results': generation_results,
            'successful_profiles': successful_profiles,
            'failed_profiles': failed_profiles,
            'total_portfolios': sum(result.get('portfolio_count', 0) for result in generation_results.values())
        }
        
        with open('PORTFOLIO_GENERATION_REPORT.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Generation report saved to PORTFOLIO_GENERATION_REPORT.json")
        
        # Final status
        if len(successful_profiles) == len(risk_profiles):
            print("\n🎉 Portfolio generation completed successfully!")
            return True
        else:
            print(f"\n⚠️ Portfolio generation completed with {len(failed_profiles)} failures")
            return False
            
    except Exception as e:
        print(f"\n❌ Critical error during portfolio generation: {e}")
        logger.error(f"Critical error: {e}", exc_info=True)
        return False


def _is_number(x) -> bool:
    try:
        return isinstance(x, (int, float)) and x == x and x not in (float('inf'), float('-inf'))
    except Exception:
        return False


def sanitize_invalid_portfolios(rds, redis_manager, enhanced_generator, portfolio_analytics, risk_profiles: List[str]) -> bool:
    """Scan all Redis portfolios; replace only those with NaN/negative expectedReturn, keep others unchanged."""
    print("\n🧹 Sanitizing portfolios: replacing NaN/negative expected returns only...")
    total_replaced = 0
    total_checked = 0

    for rp in risk_profiles:
        try:
            # Fetch existing portfolios (up to 12)
            existing = redis_manager.get_portfolio_recommendations(rp, count=12) or []
            # Rebuild by variation_id index if available
            by_index: List[Any] = [None] * max(12, len(existing) or 12)
            for p in existing:
                vid = p.get('variation_id')
                if isinstance(vid, int) and 0 <= vid < len(by_index):
                    by_index[vid] = p
                else:
                    # place into first empty slot
                    for i in range(len(by_index)):
                        if by_index[i] is None:
                            by_index[i] = p
                            break

            # Identify invalid slots
            invalid_indices: List[int] = []
            for idx, p in enumerate(by_index):
                if p is None:
                    invalid_indices.append(idx)
                    continue
                exp = p.get('expectedReturn')
                total_checked += 1
                if (not _is_number(exp)) or (float(exp) <= 0.0):
                    invalid_indices.append(idx)

            if not invalid_indices:
                print(f"  ✅ {rp}: no invalid portfolios found")
                continue

            print(f"  🔁 {rp}: replacing {len(invalid_indices)} invalid portfolios ({invalid_indices})")

            # Generate a fresh bucket and filter valid ones
            fresh = enhanced_generator.generate_portfolio_bucket(rp, use_parallel=True)
            valid_fresh = [q for q in fresh if _is_number(q.get('expectedReturn')) and float(q.get('expectedReturn')) > 0.0]
            if not valid_fresh:
                print(f"  ❌ {rp}: could not generate valid replacement portfolios")
                continue

            # Replace invalid indices with items from valid_fresh (round-robin)
            ptr = 0
            for idx in invalid_indices:
                if ptr >= len(valid_fresh):
                    # regenerate another batch if we ran out
                    fresh2 = enhanced_generator.generate_portfolio_bucket(rp, use_parallel=True)
                    more_valid = [q for q in fresh2 if _is_number(q.get('expectedReturn')) and float(q.get('expectedReturn')) > 0.0]
                    valid_fresh.extend(more_valid)
                by_index[idx] = valid_fresh[ptr]
                # ensure variation_id is set to slot index for consistency
                try:
                    by_index[idx]['variation_id'] = idx
                except Exception:
                    pass
                ptr += 1
                total_replaced += 1

            # Trim to 12
            updated_bucket = by_index[:12]
            # Store the updated bucket
            ok = redis_manager.store_portfolio_bucket(rp, updated_bucket)
            if ok:
                print(f"  ✅ {rp}: stored updated bucket with {len(invalid_indices)} replacements")
            else:
                print(f"  ❌ {rp}: failed storing updated bucket")

        except Exception as e:
            print(f"  ❌ {rp}: sanitize failed: {e}")
            continue

    # Update markdown at the end for a single write
    try:
        update_portfolios_markdown()
        print("\n📝 PORTFOLIOS_IN_REDIS.md updated after sanitization")
    except Exception as e:
        print(f"\n⚠️ Failed to update markdown: {e}")

    print(f"\n✅ Sanitization complete. Checked: {total_checked}, Replaced: {total_replaced}")
    return True

def update_portfolios_markdown():
    """Update PORTFOLIOS_IN_REDIS.md with current portfolio data"""
    from utils.redis_first_data_service import RedisFirstDataService
    from utils.redis_portfolio_manager import RedisPortfolioManager
    
    rds = RedisFirstDataService()
    redis_manager = RedisPortfolioManager(rds.redis_client)
    
    lines = [
        "# Portfolios in Redis",
        f"Generated: {datetime.now().isoformat()}",
        ""
    ]
    
    risk_profiles = ['very-conservative', 'conservative', 'moderate', 'aggressive', 'very-aggressive']
    
    # Return caps for highlighting
    caps = {
        'very-conservative': 0.12,
        'conservative': 0.15,
        'moderate': 0.25,
        'aggressive': 0.35,
        'very-aggressive': 0.45
    }
    
    total_portfolios = 0
    
    for rp in risk_profiles:
        try:
            portfolios = redis_manager.get_portfolio_recommendations(rp, count=12)
            lines.append(f"## {rp} ({len(portfolios)} portfolios)")
            lines.append("")
            
            if not portfolios:
                lines.append("*No portfolios found in Redis*")
                lines.append("")
                continue
            
            cap = caps.get(rp)
            for idx, p in enumerate(portfolios):
                total_portfolios += 1
                name = p.get('name', f'Portfolio {idx+1}')
                exp = p.get('expectedReturn')
                risk = p.get('risk')
                div = p.get('diversificationScore')
                
                # Check if above cap
                is_above_cap = False
                if cap is not None and isinstance(exp, (int, float)) and exp > cap:
                    is_above_cap = True
                
                # Format expected return
                if isinstance(exp, (int, float)):
                    exp_disp = f"{exp:.2f}"
                else:
                    exp_disp = f"{exp}"
                
                # Add header with cap warning if needed
                if is_above_cap:
                    lines.append(f"### {idx+1}. {name} ⚠️ Above cap ({cap*100:.0f}%)")
                else:
                    lines.append(f"### {idx+1}. {name}")
                
                lines.append(f"- expectedReturn: {exp_disp}")
                lines.append(f"- risk: {risk}")
                lines.append(f"- diversificationScore: {div}")
                lines.append(f"- variation_id: {p.get('variation_id')}")
                lines.append(f"- data_dependency_hash: {p.get('data_dependency_hash')}")
                lines.append(f"- generated_at: {p.get('generated_at')}")
                lines.append(f"- risk_profile: {rp}")
                lines.append("")
                lines.append("Allocations:")
                lines.append("")
                lines.append("| Symbol | Allocation | Sector | Name |")
                lines.append("|---|---:|---|---|")
                
                allocs = p.get('allocations', [])
                for alloc in allocs:
                    symbol = alloc.get('symbol', '')
                    allocation = alloc.get('allocation', 0)
                    sector = alloc.get('sector', '')
                    name_col = alloc.get('name', '')
                    lines.append(f"| {symbol} | {allocation:.1f}% | {sector} | {name_col} |")
                
                lines.append("")
                
        except Exception as e:
            lines.append(f"## {rp} (Error)")
            lines.append("")
            lines.append(f"*Error loading portfolios: {e}*")
            lines.append("")
    
    lines.append("")
    lines.append(f"Total portfolios exported: {total_portfolios}")
    lines.append("")
    
    # Write to file
    with open("PORTFOLIOS_IN_REDIS.md", 'w') as f:
        f.write('\n'.join(lines))

def setup_auto_markdown_updates():
    """Setup automatic markdown updates on portfolio changes"""
    print("\n🔄 Setting up automatic PORTFOLIOS_IN_REDIS.md updates...")
    
    # This would be implemented as a Redis listener or periodic task
    # For now, we'll create a simple update function that can be called
    try:
        # Create a simple update script that can be called
        update_script = '''#!/usr/bin/env python3
"""Auto-update PORTFOLIOS_IN_REDIS.md when portfolios change"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from generate_all_portfolios import update_portfolios_markdown

if __name__ == '__main__':
    try:
        update_portfolios_markdown()
        print("✅ PORTFOLIOS_IN_REDIS.md updated successfully")
    except Exception as e:
        print(f"❌ Failed to update markdown: {e}")
'''
        
        with open('update_portfolios_markdown.py', 'w') as f:
            f.write(update_script)
        
        print("  ✅ Auto-update script created: update_portfolios_markdown.py")
        
    except Exception as e:
        print(f"  ❌ Failed to setup auto-updates: {e}")

if __name__ == '__main__':
    success = main()
    
    # Setup auto-updates
    setup_auto_markdown_updates()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Portfolio Generation System completed successfully!")
        print("📝 PORTFOLIOS_IN_REDIS.md has been updated")
        print("🔄 Auto-update script created for future changes")
    else:
        print("⚠️ Portfolio Generation System completed with errors")
        print("📄 Check PORTFOLIO_GENERATION_REPORT.json for details")
    
    sys.exit(0 if success else 1)
