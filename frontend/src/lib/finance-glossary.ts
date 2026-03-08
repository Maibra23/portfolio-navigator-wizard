/**
 * Plain-language definitions for finance terms used in the wizard.
 * Used by FinanceTooltip to help non-finance users understand metrics and concepts.
 */

export const FINANCE_GLOSSARY: Record<string, { title: string; description: string }> = {
  sharpe_ratio: {
    title: "Sharpe Ratio",
    description:
      "How much extra return you get per unit of risk. Higher is better. Values above 1 are good, above 2 are excellent.",
  },
  efficient_frontier: {
    title: "Efficient Frontier",
    description:
      "The best possible mix of risk and return. Portfolios on this line give you the highest return for a given level of risk.",
  },
  monte_carlo: {
    title: "Monte Carlo simulation",
    description:
      "A way to test your portfolio by running thousands of random market scenarios. It shows a range of possible outcomes, not a single prediction.",
  },
  volatility: {
    title: "Volatility",
    description:
      "How much your investment value tends to swing up and down. Higher volatility means bigger swings; lower means more stable.",
  },
  volatility_tolerance: {
    title: "Volatility tolerance",
    description:
      "How comfortable you are with your portfolio value going up and down in the short term.",
  },
  mvo: {
    title: "Mean-Variance Optimization (MVO)",
    description:
      "A method to find the best mix of investments that balances expected return with the amount of risk you are willing to take.",
  },
  sortino_ratio: {
    title: "Sortino Ratio",
    description:
      "Like Sharpe ratio but only counts downside risk (losses). It measures how well your portfolio rewards you for the risk of losing money.",
  },
  drawdown: {
    title: "Drawdown",
    description:
      "How much your portfolio drops from its peak during a bad period. A 20% drawdown means your portfolio fell 20% from its highest point.",
  },
  max_drawdown: {
    title: "Maximum Drawdown",
    description:
      "The largest peak-to-trough drop your portfolio has had (or could have in simulations). It shows the worst decline in value.",
  },
  expected_return: {
    title: "Expected return",
    description:
      "The average return you might expect from your portfolio over time, based on historical data. Not a guarantee.",
  },
  risk_adjusted_return: {
    title: "Risk-adjusted return",
    description:
      "Return compared to how much risk you took. A portfolio with higher risk-adjusted return gives you more reward for the risk you accept.",
  },
  diversification: {
    title: "Diversification",
    description:
      "Spreading your money across different investments so that if one does poorly, others may do better. It can reduce overall risk.",
  },
  correlation: {
    title: "Correlation",
    description:
      "How two investments tend to move together. Low or negative correlation helps diversification; high correlation means they move in sync.",
  },
  var: {
    title: "Value at Risk (VaR)",
    description:
      "Under normal conditions, the most you could expect to lose in a given period (e.g. 95% of the time you won't lose more than X%).",
  },
  cvar: {
    title: "Conditional VaR (CVaR)",
    description:
      "When things go badly, how bad can it get on average? CVaR looks at the worst outcomes beyond the VaR threshold.",
  },
  beta: {
    title: "Beta",
    description:
      "How much your portfolio tends to move with the overall market. Beta of 1 means it moves with the market; above 1 means more volatile.",
  },
  tail_risk: {
    title: "Tail risk",
    description:
      "The risk of rare but very bad events (like sharp market crashes). It's the chance of extreme losses.",
  },
  recovery_time: {
    title: "Recovery time",
    description:
      "How long it typically took (or might take) for your portfolio to bounce back to its previous peak after a drop.",
  },
};

export type FinanceGlossaryKey = keyof typeof FINANCE_GLOSSARY;

export function getGlossaryEntry(key: string): { title: string; description: string } | undefined {
  return FINANCE_GLOSSARY[key as FinanceGlossaryKey];
}
