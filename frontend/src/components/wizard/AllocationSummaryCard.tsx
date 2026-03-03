import { motion } from 'framer-motion';

interface AllocationSummaryCardProps {
  stockCount: number;
  totalAllocation: number;
  isValid: boolean;
  className?: string;
}

export function AllocationSummaryCard({
  stockCount,
  totalAllocation,
  isValid,
  className = '',
}: AllocationSummaryCardProps) {
  const isOverAllocated = totalAllocation > 100;

  return (
    <motion.div
      key={isOverAllocated ? 'over' : 'ok'}
      className={`border rounded-lg p-3 ${isOverAllocated ? 'alert-error' : 'bg-muted/30'} ${className}`}
      animate={isOverAllocated ? { x: [0, -6, 6, -6, 6, 0] } : { x: 0 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
    >
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <div className="text-xl font-bold text-primary">{stockCount}</div>
          <div className="text-xs text-muted-foreground">Stocks</div>
        </div>
        <div>
          <div
            className={`text-xl font-bold ${totalAllocation > 100 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}
          >
            {totalAllocation.toFixed(1)}%
          </div>
          <div className="text-xs text-muted-foreground">Total Allocation</div>
        </div>
        <div>
          <div
            className={`text-xl font-bold ${totalAllocation > 100 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}
          >
            {totalAllocation > 100 ? '✗' : '✓'}
          </div>
          <div className="text-xs text-muted-foreground">Status</div>
        </div>
      </div>
      <div
        className={`mt-2 text-center text-xs ${totalAllocation > 100 ? 'text-red-600 dark:text-red-400 font-medium' : 'text-muted-foreground'}`}
      >
        Total Allocation: {totalAllocation.toFixed(1)}%
      </div>
    </motion.div>
  );
}
