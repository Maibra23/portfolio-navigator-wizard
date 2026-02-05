import { PortfolioState } from '@/hooks/usePortfolioState';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export const validateTab = (
  tabId: string,
  state: PortfolioState
): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  switch (tabId) {
    case 'builder':
      // Tab 1 validation: 3-4 stocks required to proceed; 100% allocation recommended
      const stockCount = state.constructedPortfolio.length;
      const totalAllocation = state.constructedPortfolio.reduce(
        (sum, stock) => sum + (stock.allocation || 0),
        0
      );

      if (stockCount < 3) {
        errors.push(`You need at least 3 stocks. Currently have ${stockCount}.`);
      }
      if (stockCount > 4) {
        errors.push(`Maximum 4 stocks allowed. Currently have ${stockCount}.`);
      }
      if (Math.abs(totalAllocation - 100) > 0.1) {
        warnings.push(`Total allocation should equal 100%. Currently at ${totalAllocation.toFixed(1)}%.`);
      }

      // Allow navigation to Optimize when 3-4 stocks are selected (allocation can be fixed on next step)
      if (stockCount >= 3 && stockCount <= 4) {
        return { isValid: true, errors: [], warnings };
      }

      break;

    case 'optimize':
      // Tab 2 validation: Optimization must be completed
      if (!state.optimizedPortfolio) {
        errors.push('Optimization must be completed before proceeding.');
      } else {
        return { isValid: true, errors: [], warnings: [] };
      }
      break;

    case 'analysis':
      // Tab 3 validation: Require optimization to be completed
      if (!state.optimizedPortfolio) {
        errors.push('Please complete portfolio optimization before viewing analysis.');
      }
      // Also ensure portfolio was built
      if (state.constructedPortfolio.length === 0) {
        errors.push('Please build a portfolio first.');
      }

      if (errors.length === 0) {
        return { isValid: true, errors: [], warnings: [] };
      }
      break;

    case 'tax-cost':
      // Tab 4 validation: Account type must be selected for export
      if (!state.taxSettings.accountType) {
        warnings.push('Account type must be selected before exporting.');
        // This is a warning, not an error - user can still view the tab
        return { isValid: true, errors: [], warnings };
      }
      return { isValid: true, errors: [], warnings: [] };

    default:
      return { isValid: true, errors: [], warnings: [] };
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

export const canNavigateToTab = (
  targetTab: string,
  state: PortfolioState,
  currentTab: string
): boolean => {
  const tabOrder = ['builder', 'optimize', 'analysis', 'tax-cost'];
  const currentTabIndex = tabOrder.indexOf(currentTab);
  const targetTabIndex = tabOrder.indexOf(targetTab);

  // Always allow backward navigation
  if (targetTabIndex <= currentTabIndex) {
    return true;
  }

  // Optimize → Analysis: allow if optimization was run (user may have selected an optimized portfolio with different stock count)
  if (currentTab === 'optimize' && targetTab === 'analysis') {
    return Boolean(state.optimizedPortfolio && state.constructedPortfolio.length > 0);
  }

  // Analysis → Tax-cost: allow if user reached analysis (optimization done, portfolio present)
  if (currentTab === 'analysis' && targetTab === 'tax-cost') {
    return Boolean(state.optimizedPortfolio && state.constructedPortfolio.length > 0);
  }

  // For forward navigation, validate ALL previous tabs
  for (let i = 0; i < targetTabIndex; i++) {
    const tabId = tabOrder[i];
    const validation = validateTab(tabId, state);
    if (!validation.isValid) {
      return false;
    }
  }

  return true;
};
