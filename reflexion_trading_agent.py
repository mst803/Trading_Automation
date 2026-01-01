import os
import yfinance as yf
from langchain_core.output_parsers import PydanticOutputParser
from schema_reflexion import TradingSignal
from langchain_perplexity import ChatPerplexity
from perplexity import Perplexity
from datetime import datetime
from time import sleep
from prompts import PROMPT_1, PROMPT_2, PROMPT_3, PROMPT_4
from dotenv import load_dotenv
load_dotenv()

# class CustomPerplexity(ChatPerplexity):
#     def _generate(self, messages, stop=None, **kwargs):
#         return super()._generate(messages, stop=None, **kwargs)

# llm = CustomPerplexity(api_key=os.environ.get("PERPLEXITY_API_KEY"), temperature=0, model="sonar-deep-research") #sonar-deep-research
# llm_mini = CustomPerplexity(api_key=os.environ.get("PERPLEXITY_API_KEY"), temperature=0, model="sonar")


client = Perplexity(api_key=os.environ.get("PERPLEXITY_API_KEY"))

def get_responce(prompt: str, model: str = "sonar-pro"):
    res = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return res.choices[0].message


def fetch_stock_data(stock_Name: str):
    """Fetch real stock data from yfinance with error handling"""
    ticker = yf.Ticker(stock_Name)
    hist = ticker.history(period="7d", interval="1h")
    
    if hist.empty:
        print("⚠️  No historical data available")
        return {"error": "No data", "data_available": False}
    
    current_price = float(hist['Close'].iloc[-1])
    prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0
    
    data = {
        "current_price": round(current_price, 2),
        "previous_close": round(prev_close, 2),
        "price_change": round(current_price - prev_close, 2),
        "price_change_pct": round(change_pct, 2),
        "volume_avg": round(float(hist['Volume'].mean()), 0),
        "52w_high": round(float(hist['Close'].max()), 2),
        "52w_low": round(float(hist['Close'].min()), 2),
        "historical_data": hist.to_csv(index=False) if not hist.empty else []
    }
    return data


def get_signal(stock_Name: str):
    p1 = PROMPT_1.format(time=datetime.now().isoformat(),stock_Name = stock_Name, stock_statistics = fetch_stock_data(stock_Name))
    res1 = get_responce(p1)
    text_response1 = res1.content
    if '</think>' in text_response1:
        text_response1 = text_response1.split('</think>')[1]
    sleep(180)
    p2 = PROMPT_2.format(response=text_response1, time=datetime.now().isoformat(), stock_Name = stock_Name, stock_statistics = fetch_stock_data(stock_Name))
    res2 = get_responce(p2)
    text_response2 = res2.content
    if '</think>' in text_response2:
        text_response2 = text_response2.split('</think>')[1]

    p3 = PROMPT_3.format(response=text_response1, review = text_response2, time=datetime.now().isoformat(), stock_Name = stock_Name, stock_statistics = fetch_stock_data(stock_Name))
    res3 = get_responce(p3)
    text_response3 = res3.content
    if '</think>' in text_response3:
        text_response3 = text_response3.split('</think>')[1]


    base_parser = PydanticOutputParser(pydantic_object=TradingSignal)
    p4 = PROMPT_4.format(response=text_response3, base_parser = base_parser.get_format_instructions(), time=datetime.now().isoformat(), stock_Name = stock_Name)
    res4 = get_responce(p4, model="sonar")
    signal = base_parser.parse(res4.content).signal.value

    return signal