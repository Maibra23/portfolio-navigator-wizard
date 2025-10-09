# Risk Profile Classification System 📊

## Overview

The Portfolio Navigator Wizard uses a sophisticated risk profiling system that classifies users into 5 distinct risk categories based on their responses to carefully designed questions. This system combines Modern Portfolio Theory (MPT) principles with behavioral finance insights.

## 🎯 Risk Profile Categories

### 1. Very Conservative (0-19% score)
- **Color Code**: #00008B (Dark Blue)
- **Characteristics**:
  - Maximum capital preservation focus
  - Very low risk tolerance
  - Income-focused investments
  - Short-term thinking
- **Typical Allocation**: 70% bonds, 25% stocks, 5% REITs
- **Investment Style**: Prefers guaranteed returns over growth potential

### 2. Conservative (20-39% score)
- **Color Code**: #ADD8E6 (Light Blue)
- **Characteristics**:
  - Capital preservation focused
  - Prefers steady returns
  - Lower volatility tolerance
  - Income-oriented investments
- **Typical Allocation**: 50% bonds, 40% stocks, 10% REITs
- **Investment Style**: Stability over growth, dividend-paying stocks

### 3. Moderate (40-59% score)
- **Color Code**: #008000 (Green)
- **Characteristics**:
  - Balanced risk-return approach
  - Diversified portfolio
  - Medium-term growth focus
  - Some volatility tolerance
- **Typical Allocation**: 30% bonds, 60% stocks, 10% REITs
- **Investment Style**: Balanced growth with moderate risk

### 4. Aggressive (60-79% score)
- **Color Code**: #FFA500 (Orange)
- **Characteristics**:
  - High growth potential focus
  - High risk tolerance
  - Long-term focused
  - Comfortable with volatility
- **Typical Allocation**: 15% bonds, 75% stocks, 10% REITs
- **Investment Style**: Growth stocks and emerging markets

### 5. Very Aggressive (80-100% score)
- **Color Code**: #FF0000 (Red)
- **Characteristics**:
  - Maximum growth potential
  - Very high risk tolerance
  - Long-term horizon
  - Thrives on volatility
- **Typical Allocation**: 5% bonds, 85% stocks, 10% REITs
- **Investment Style**: High-growth tech stocks, emerging markets, alternatives

## 📋 Scoring System

### Question Types

#### 1. Modern Portfolio Theory (MPT) Questions
- **Purpose**: Assess understanding of investment fundamentals
- **Examples**:
  - Asset allocation preferences (stocks vs bonds)
  - Investment time horizon
  - Risk tolerance in different scenarios
- **Scoring**: 1-5 scale per question

#### 2. Prospect Theory Questions
- **Purpose**: Assess behavioral biases and loss aversion
- **Examples**:
  - Guaranteed vs. risky outcomes
  - Loss aversion scenarios
  - Risk-taking in gains vs losses
- **Scoring**: 1-5 scale per question

#### 3. Gamified Storyline (for users under 19)
- **Purpose**: Engage younger users with relatable scenarios
- **Examples**:
  - Gaming tournament prize money decisions
  - Investment choices in familiar contexts
- **Scoring**: 1-4 scale per scenario

### Calculation Method

```typescript
// Raw score calculation
const rawScore = Object.values(answers).reduce((sum, score) => sum + score, 0);

// Normalized score (0-100%)
const normalizedScore = (rawScore / (selectedQuestions.length * 5)) * 100;

// Risk category assignment
if (normalizedScore <= 19) riskCategory = 'very-conservative';
else if (normalizedScore <= 39) riskCategory = 'conservative';
else if (normalizedScore <= 59) riskCategory = 'moderate';
else if (normalizedScore <= 79) riskCategory = 'aggressive';
else riskCategory = 'very-aggressive';
```

## 🔧 Implementation Files

### Primary Risk Profiler Component
**File**: `frontend/src/components/wizard/RiskProfiler.tsx`

**Key Functions**:
- `calculateRiskProfile()`: Main scoring algorithm
- `determineQuestionMix()`: Question selection based on user demographics
- `selectQuestions()`: Dynamic question pool selection
- `getProfileInfo()`: Profile characteristics and descriptions

### Question Pools
**Location**: `frontend/src/components/wizard/RiskProfiler.tsx`

**Constants**:
- `MPT_QUESTIONS[]`: Modern Portfolio Theory questions
- `PROSPECT_QUESTIONS[]`: Behavioral finance questions
- `GAMIFIED_STORYLINE[]`: Gamified scenarios for young users

### Risk Profile Integration
**File**: `frontend/src/components/wizard/StockSelection.tsx`

**Key Functions**:
- `generateRecommendations()`: Risk-adjusted portfolio recommendations
- `getRiskProfileDisplay()`: Profile name formatting

## 🎨 Visual Indicators

### Color Coding System
Each risk profile has a distinct color for visual identification:
- **Very Conservative**: Dark Blue (#00008B)
- **Conservative**: Light Blue (#ADD8E6)
- **Moderate**: Green (#008000)
- **Aggressive**: Orange (#FFA500)
- **Very Aggressive**: Red (#FF0000)

### UI Elements
- Risk profile badges in portfolio recommendations
- Color-coded progress indicators
- Profile-specific messaging and guidance

## 📊 Risk Profile Adjustments

### Portfolio Recommendations
The system adjusts portfolio recommendations based on risk profile:

```typescript
const riskAdjustments = {
  'very-conservative': { returnMultiplier: 0.7, riskMultiplier: 0.6 },
  'conservative': { returnMultiplier: 0.85, riskMultiplier: 0.75 },
  'moderate': { returnMultiplier: 1.0, riskMultiplier: 1.0 },
  'aggressive': { returnMultiplier: 1.15, riskMultiplier: 1.25 },
  'very-aggressive': { returnMultiplier: 1.3, riskMultiplier: 1.5 }
};
```

### Question Mix Adaptation
The system adapts question types based on user demographics:
- **Under 19**: 80% gamified, 20% MPT
- **High Experience**: 80% MPT, 20% Prospect Theory
- **Default**: 30% MPT, 70% Prospect Theory

## 🔍 Data Flow

1. **Screening Phase**: Collect user demographics (age, experience, knowledge)
2. **Question Selection**: Choose appropriate question mix
3. **Answer Collection**: Gather responses with scoring
4. **Profile Calculation**: Compute normalized score and assign category
5. **Integration**: Apply risk profile to portfolio recommendations
6. **Visual Feedback**: Display profile-specific UI elements

## 🎯 Key Features

- **Adaptive Questioning**: Questions adjust based on user age and experience
- **Behavioral Insights**: Incorporates prospect theory for realistic risk assessment
- **Gamified Experience**: Engaging scenarios for younger users
- **Real-time Integration**: Risk profile immediately affects portfolio recommendations
- **Visual Consistency**: Color-coded system throughout the application

## 📈 Future Enhancements

- **Machine Learning**: Adaptive scoring based on user behavior patterns
- **Market Conditions**: Dynamic risk adjustments based on market volatility
- **Personalization**: Individualized question weighting based on demographics
- **Validation**: Backtesting risk profiles against actual investment behavior 