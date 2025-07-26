import numpy


def recognise_hammer_pattern(data,tf):
        if data.empty:
            return False
        # print("*******")
        # # print(data)
        # print("*******")
        low = numpy.min(data["low"])
        high = numpy.max(data["high"])
        open = data["open"].iloc[0]
        close = data["close"].iloc[-1]
        body = abs(close - open)
        wick = abs(high-low)
        # print(open[0])
            
        
        return {
        "script": data["symbolcode"],
        "low": low,
        "open": open,
        "high": high,
        "close": close,
        "detected": (abs(open - high) == 0 or abs(low - open) == 0 ) and (wick / body > 2),
        "created": data.index[0] , # First timestamp in group,
        "pattern":"hammer",
        "tf":tf
    }

