import { motion } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  format?: 'percent' | 'decimal' | 'integer';
  decimals?: number;
  className?: string;
}

const defaultFormat = (value: number, format: 'percent' | 'decimal' | 'integer', decimals: number): string => {
  if (format === 'percent') return `${(value * 100).toFixed(decimals)}%`;
  if (format === 'integer') return Math.round(value).toString();
  return value.toFixed(decimals);
};

export function AnimatedNumber({ value, format = 'decimal', decimals = 2, className }: AnimatedNumberProps) {
  const display = defaultFormat(value, format, decimals);

  return (
    <motion.span
      key={display}
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {display}
    </motion.span>
  );
}
