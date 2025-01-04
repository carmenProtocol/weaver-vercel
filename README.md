# Weaver Trading Strategy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/weaver.git
cd weaver
```

2. Create and activate a virtual environment (recommended):
```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install the package and dependencies:
```bash
# Install basic requirements
pip install ccxt python-dotenv

# For full functionality, install all dependencies
pip install -e .
```

4. Configure your API credentials:
```bash
cp .env.example .env
# Edit .env with your OKX API credentials
```

## Usage

1. Make sure your OKX API credentials are properly set in the `.env` file.

2. Run the trading bot:
```bash
python main.py
```

The bot will automatically:
- Initialize the trading strategy
- Monitor market prices
- Execute trades based on the strategy rules
- Manage hedge positions
- Track and display performance metrics

## Configuration

Key configuration parameters can be adjusted in `config.py`:
- Trading pair settings
- Risk management parameters
- Position size limits
- Hedge ratios
- Rebalancing thresholds

## Project Structure

```
weaver/
├── config.py       # Configuration parameters and constants
├── state.py        # Strategy state management and persistence
├── data_fetcher.py # Market data retrieval and processing
├── scanner.py      # Market scanning for optimal trading opportunities
├── strategy.py     # Core trading logic and calculations
├── executor.py     # Order execution and management
├── analyzer.py     # Performance analysis and reporting
└── main.py        # Strategy initialization and main loop
```

## Warning

**This is a cryptocurrency trading bot. Trading cryptocurrencies involves significant risk of loss and is not suitable for all investors. The use of this software is entirely at your own risk.**

## License

This project is licensed under the MIT License - see the LICENSE file for details. 