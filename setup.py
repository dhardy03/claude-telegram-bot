from setuptools import setup

setup(
    name="claude-telegram-bot",
    version="1.0.0",
    py_modules=["bot", "chat"],
    install_requires=[
        "anthropic==0.97.0",
        "python-telegram-bot==22.7",
        "fastapi==0.115.12",
        "uvicorn[standard]==0.34.2",
        "python-dotenv==1.2.2",
        "google-cloud-firestore==2.27.0",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "claude-bot=bot:main",
            "R2D2-bot=chat:chat",
        ],
    },
)
