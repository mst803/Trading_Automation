import os
import time
import logging
from datetime import time as dt_time, datetime
from reflexion_trading_agent import get_signal
import yfinance as yf
from kiteconnect import KiteConnect
from kite_authenticate import request_token_generator
from dotenv import load_dotenv
load_dotenv()

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class TradingBot:

    def __init__(self, api_key, api_secret, symbol, interval=3600):
        self.kite = KiteConnect(api_key=api_key)
        self.api_secret = api_secret
        self.symbol = symbol.upper()
        self.interval = interval

        self.position_qty = 0
        self.entry_price = 0.0
        self.session_active = False

    # =========================
    # LOGIN
    # =========================
    def login(self):
        request_token = request_token_generator(self.kite.login_url())
        data = self.kite.generate_session(request_token, self.api_secret)
        self.kite.set_access_token(data["access_token"])
        self.session_active = True

        logger.info("Kite login successful")

    # =========================
    # PRICE
    # =========================
    def get_ltp(self):
        ticker = yf.Ticker(f"{self.symbol}.NS")
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            return None

        return float(data.iloc[-1]["Close"])

    # =========================
    # WALLET
    # =========================
    def get_wallet(self):
        margins = self.kite.margins("equity")
        return float(margins["available"]["intraday_payin"])+float(margins["available"]["cash"])

    def calc_qty(self, ltp):
        cash = self.get_wallet()*0.95
        return int(cash // ltp)*5

    # =========================
    # ORDERS
    # =========================
    def buy(self, qty):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=self.kite.EXCHANGE_NSE,
            tradingsymbol=self.symbol,
            transaction_type=self.kite.TRANSACTION_TYPE_BUY,
            quantity=abs(qty),
            order_type=self.kite.ORDER_TYPE_MARKET,
            product=self.kite.PRODUCT_MIS
        )

    def sell(self, qty):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=self.kite.EXCHANGE_NSE,
            tradingsymbol=self.symbol,
            transaction_type=self.kite.TRANSACTION_TYPE_SELL,
            quantity=abs(qty),
            order_type=self.kite.ORDER_TYPE_MARKET,
            product=self.kite.PRODUCT_MIS
        )

    # =========================
    # MAIN LOOP
    # =========================
    def run(self):
        if not self.session_active:
            raise Exception("Not logged in")

        logger.info("Trading started")

        while True:
            if datetime.now().time()>dt_time(15, 15):
                logger.info("Market closed. Exiting.")
                break

            ltp = self.get_ltp()
            if not ltp:
                time.sleep(360)
                continue

            signal = get_signal(self.symbol + ".NS")
            print(signal)
            logger.info(f"Signal={signal} | LTP={ltp}")

            if signal == "HOLD":
                if datetime.now().time()>dt_time(14, 15):
                    logger.info("Market closed. Exiting.")
                    break
                time.sleep(self.interval)
                logger.info("Bot woke up, checking market...")
                continue

            if (signal == "BUY" and self.position_qty>0) or (signal == "SELL" and self.position_qty<0):
                if datetime.now().time()>dt_time(14, 15):
                    logger.info("Market closed. Exiting.")
                    break
                time.sleep(self.interval)
                continue

            # ================= BUY =================
            if signal == "BUY" and self.position_qty == 0:
                qty = self.calc_qty(ltp)
                if qty > 0:
                    self.buy(qty)
                    self.position_qty = qty
                    self.entry_price = ltp
                    logger.info(f"BOUGHT {qty} @ {ltp}")
                else:
                    print("Insufficient funds to buy")

            # ================= Double BUY =================
            if signal == "BUY" and self.position_qty < 0:
                self.buy(abs(self.position_qty))
                time.sleep(2)
                qty = self.calc_qty(ltp)
                if qty > 0:
                    self.buy(qty)
                    self.position_qty = qty

            # ================= SELL =================
            if signal == "SELL" and self.position_qty == 0:
                qty = self.calc_qty(ltp)
                if qty > 0:
                    self.sell(qty)
                    self.position_qty = -qty
                    self.entry_price = ltp
                    logger.info(f"SOLD {qty} @ {ltp}")

            # ================= Double SELL =================
            elif signal == "SELL" and self.position_qty > 0:
                self.sell(self.position_qty)
                time.sleep(2)
                qty = self.calc_qty(ltp)
                if qty > 0:
                    self.sell(qty)
                    self.position_qty = -qty

            if datetime.now().time()>dt_time(14, 15):
                logger.info("Market closed. Exiting.")
                break
            time.sleep(self.interval)

        while datetime.now().time()<dt_time(15, 15):
            time.sleep(60)
            logger.info("Waiting for market to close...")

        if self.position_qty > 0:
            self.sell(self.position_qty)
            logger.info(f"EXITED {self.position_qty} @ {self.get_ltp()}")
        elif self.position_qty < 0:
            self.buy(self.position_qty)
            logger.info(f"EXITED {abs(self.position_qty)} @ {self.get_ltp()}")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot = TradingBot(
        api_key=os.getenv("kite_api_key"),
        api_secret=os.getenv("kite_api_secret"),
        symbol="SUZLON",
        interval=360
    )

    # bot.login()
    # bot.run()
