import asyncio
from datetime import datetime, timezone
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
TOKEN = "8232198206:AAHz2GHiKWQAcMKTF-Iz5Nl_Haatsi4ol_o"   # <-- yahan tumhara token fill hai

# Mapping: command -> (Binance symbol, CoinGecko ID, Display Name)
COINS = {
    "ton": ("TONUSDT", "the-open-network", "Toncoin"),
    "sol": ("SOLUSDT", "solana", "Solana"),
    "btc": ("BTCUSDT", "bitcoin", "Bitcoin"),
    "eth": ("ETHUSDT", "ethereum", "Ethereum"),
    "ltc": ("LTCUSDT", "litecoin", "Litecoin"),
}
# ===========================================


async def fetch_json(session: aiohttp.ClientSession, url: str, params: dict | None = None):
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
        r.raise_for_status()
        return await r.json()


async def get_price(symbol: str, cg_id: str) -> dict:
    async with aiohttp.ClientSession() as session:
        # Binance
        try:
            data = await fetch_json(session, "https://api.binance.com/api/v3/ticker/price", {"symbol": symbol})
            price = float(data["price"])
            return {"price": price, "source": "Binance", "ts": datetime.now(timezone.utc)}
        except Exception:
            pass

        # CoinGecko
        try:
            data = await fetch_json(
                session,
                "https://api.coingecko.com/api/v3/simple/price",
                {"ids": cg_id, "vs_currencies": "usd"},
            )
            price = float(data[cg_id]["usd"])
            return {"price": price, "source": "CoinGecko", "ts": datetime.now(timezone.utc)}
        except Exception as e:
            raise RuntimeError(f"Failed fetching {symbol}: {e}")


def format_price(name: str, info: dict) -> str:
    ts = info["ts"].strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"💰 {name} Price\n• USD: ${info['price']:.4f}\n• Source: {info['source']}\n• Updated: {ts}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = "\n".join([f"/{c} — {COINS[c][2]}" for c in COINS])
    await update.message.reply_text(
        "👋 Welcome! Main live crypto prices dikhata hu.\n\n"
        "Available commands:\n"
        f"{cmds}\n"
        "/all — sabka price ek sath\n"
        "/convert {amount} {coin} — Example: /convert 2 btc"
    )


def make_handler(cmd: str, symbol: str, cg_id: str, disp: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            info = await get_price(symbol, cg_id)
            await update.message.reply_text(format_price(disp, info))
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
    return handler


async def all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msgs = []
    for cmd, (symbol, cg_id, disp) in COINS.items():
        try:
            info = await get_price(symbol, cg_id)
            msgs.append(f"{disp}: ${info['price']:.4f} ({info['source']})")
        except Exception as e:
            msgs.append(f"{disp}: Error {e}")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = "📊 All Prices\n" + "\n".join(msgs) + f"\n\nUpdated: {ts}"
    await update.message.reply_text(text)


async def convert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /convert {amount} {coin}\nExample: /convert 2 btc")
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number.\nExample: /convert 2 btc")
        return

    coin = context.args[1].lower()
    if coin not in COINS:
        await update.message.reply_text(f"❌ Unsupported coin. Available: {', '.join(COINS.keys())}")
        return

    symbol, cg_id, disp = COINS[coin]
    try:
        info = await get_price(symbol, cg_id)
        usd_value = amount * info["price"]
        ts = info["ts"].strftime("%Y-%m-%d %H:%M:%S UTC")
        text = (
            f"🔄 Convert\n"
            f"{amount} {disp} = ${usd_value:,.2f}\n"
            f"(1 {disp} = ${info['price']:.4f})\n"
            f"Source: {info['source']}\nUpdated: {ts}"
        )
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    for cmd, (symbol, cg_id, disp) in COINS.items():
        app.add_handler(CommandHandler(cmd, make_handler(cmd, symbol, cg_id, disp)))

    app.add_handler(CommandHandler("all", all_handler))
    app.add_handler(CommandHandler("convert", convert_handler))

    print("Bot started...")
    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
