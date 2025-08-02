# XAuto - Twitter Automation Tool

A powerful GUI-based Twitter automation tool built with Python, Selenium, and OpenAI integration. Automate replies, comments, and AI-powered interactions on Twitter/X.

## 🚀 Features

- **Multi-Account Management**: Manage multiple Twitter accounts with persistent login sessions
- **AI-Powered Comments**: Generate contextual comments using OpenAI GPT-4
- **Bulk Operations**: Reply to tweets and comments across multiple accounts
- **Smart Scraping**: Extract tweet content and comments for context analysis
- **Rate Limiting**: Built-in API rate limiting and cost tracking
- **Modern GUI**: Clean, responsive interface built with Tkinter
- **Browser Automation**: Undetected ChromeDriver for reliable automation

## 📋 Requirements

- Python 3.8+
- Chrome/Chromium browser
- OpenAI API key (for AI features)
- Twitter accounts

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/xauto.git
cd xauto
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Copy `sample_env.txt` to `.env` and add your API keys:

```bash
cp sample_env.txt .env
# Edit .env with your actual API keys
```

### 4. Configure Accounts

Copy `sample_accounts.json` to `accounts.json` and add your accounts:

```bash
cp sample_accounts.json accounts.json
# Edit accounts.json with your actual account data
```

## ⚙️ Configuration

### Environment Variables (.env)

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.8

# Rate Limiting
MAX_CALLS_PER_MINUTE=60
MAX_CALLS_PER_HOUR=1000

# Budget Settings
DAILY_BUDGET=10.00
MONTHLY_BUDGET=100.00
```

### Account Configuration (accounts.json)

```json
{
  "accounts": [
    {
      "label": "My Account",
      "username": "myusername",
      "email": "myemail@example.com",
      "password": "mypassword",
      "tags": ["personal", "main"],
      "proxy": "",
      "notes": "My main account"
    }
  ]
}
```

## 🎯 Usage

### Starting the Application

```bash
python -m gui.main_app
```

### Available Panels

1. **Dashboard**: Overview and quick actions
2. **Accounts**: Manage Twitter accounts and login status
3. **Reply**: Bulk reply to tweets across multiple accounts
4. **Yapping**: AI-powered comment generation and auto-reply
5. **Reply Comments**: Reply to specific comments on tweets
6. **DM**: Send direct messages
7. **AI Settings**: Configure OpenAI integration and rate limits
8. **History**: View operation logs and history

### Key Features

#### AI-Powered Comments

- Generate contextual comments using OpenAI
- Custom prompts for specific interaction styles
- Rate limiting and cost tracking
- Bulk generation across multiple accounts

#### Smart Scraping

- Extract tweet content and context
- Gather comments for better AI understanding
- Handle rate limits and errors gracefully

#### Browser Automation

- Persistent login sessions
- Anti-detection measures
- Optimized performance
- Automatic cleanup

## 🔧 Troubleshooting

### Common Issues

1. **Browser Not Opening**

   - Ensure Chrome is installed
   - Check ChromeDriver compatibility
   - Try running in non-headless mode

2. **Login Issues**

   - Verify account credentials
   - Check for 2FA requirements
   - Clear browser profiles if needed

3. **API Errors**

   - Verify OpenAI API key
   - Check rate limits and billing
   - Ensure proper .env configuration

4. **Selector Issues**
   - Twitter UI changes may affect selectors
   - Check for updates to the tool
   - Report issues with screenshots

### Performance Optimization

- Use headless mode for faster operations
- Reduce the number of Chrome options
- Close browsers after operations
- Monitor API usage and costs

## 📁 Project Structure

```
xAuto/
├── gui/                    # GUI components
│   ├── panels/            # Individual panel modules
│   └── main_app.py        # Main application entry
├── ai_integration.py      # OpenAI integration
├── selenium_manager.py    # Browser automation
├── account_manager.py     # Account management
├── utils.py              # Utility functions
├── constants.py          # Constants and configurations
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── .gitignore           # Git ignore rules
├── sample_accounts.json # Sample account configuration
├── sample_env.txt       # Sample environment variables
└── SETUP_GITHUB.md     # GitHub setup guide
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and personal use only. Please comply with Twitter's Terms of Service and API usage guidelines. The developers are not responsible for any misuse of this tool.

## 🆘 Support

- Create an issue on GitHub for bugs
- Check the troubleshooting section
- Review the documentation
- Test with sample data first

## 🔄 Updates

- Regular updates for Twitter UI changes
- Performance optimizations
- New features and improvements
- Security updates

---

**Note**: Always test with sample data before using with real accounts. Keep your API keys and account credentials secure.

## 🔧 Proxy Support

The application supports both HTTP and SOCKS5 proxies for enhanced privacy and location flexibility.

### Supported Formats:

- **HTTP Proxies**: `ip:port`, `ip:port:user:pass`, `http://ip:port`
- **SOCKS5 Proxies**: `socks5://ip:port`, `socks5://ip:port:user:pass`

### Adding Proxies:

1. Go to **Accounts** panel → Click **"Manage Proxies"**
2. Use **"Mass Import"** for bulk proxy files
3. Use **"Add Single"** for individual proxies
4. Test proxies with **"Test Selected"** or **"Test All"**

### SOCKS5 Testing:

For SOCKS5 proxy testing, install additional support:

```bash
python install_socks_support.py
```

Or manually:

```bash
pip install requests[socks]
```

### Recommended Proxy Providers:

- **Residential Proxies**: Bright Data, Oxylabs, SmartProxy
- **Datacenter Proxies**: ProxyMesh, ProxyRack
- **Free Proxies**: Use with caution (limited reliability)

### Benefits:

- **Privacy**: Hide your real IP address
- **Location**: Access geo-restricted content
- **Rate Limiting**: Avoid IP-based rate limits
- **Account Safety**: Reduce detection risk
