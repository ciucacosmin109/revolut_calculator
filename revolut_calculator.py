import sys
import pandas as pd

pd.options.display.float_format = "{:,.8f}".format
pd.options.display.max_rows = 50
pd.options.display.max_columns = 10
pd.options.display.width = 256


def get_buy_data(data, stock_code, before_index):
    buy = data[(data["Ticker"] == stock_code) & (data.index < before_index)]
    filter_activities = ["BUY", "SELL", "STOCK SPLIT"]
    buy = buy[buy["Type"].isin(filter_activities)]

    buy_quantity = 0
    buy_amount = 0
    avg_buy_price = 0

    for i in buy.index:

        activity = buy["Type"][i]
        if activity == "BUY" or activity == "STOCK SPLIT":
            buy_quantity += buy["Quantity"][i]

            if activity == "BUY":
                buy_amount += buy["Total Amount"][i]

            if buy_quantity != 0:
                avg_buy_price = buy_amount / buy_quantity

        elif activity == "SELL":
            buy_quantity -= buy["Quantity"][i]
            buy_amount = avg_buy_price * buy_quantity

            if buy_amount == 0:
                avg_buy_price = 0

    return avg_buy_price, buy_quantity, buy_amount


def get_sell_profit(data, at_index):
    sell_instance = data[data.index == at_index]
    stock_code = sell_instance["Ticker"][at_index]
    sell_amount = sell_instance["Total Amount"][at_index]
    sell_quantity = sell_instance["Quantity"][at_index]

    avg_buy_price, buy_quantity, buy_amount = get_buy_data(data, stock_code, at_index)

    # check if there is a partial sell
    eps = 0.000000001
    if buy_quantity > sell_quantity and buy_quantity - sell_quantity > eps:
        avg_buy_price = buy_amount / buy_quantity
        return sell_amount - sell_quantity * avg_buy_price
    else:
        return sell_amount - buy_amount


def get_pre_and_post_quantities(data, at_index):
    sell_instance = data[data.index == at_index]
    stock_code = sell_instance["Ticker"][at_index]
    sell_quantity = sell_instance["Quantity"][at_index]

    _, before_sell_quantity, _ = get_buy_data(data, stock_code, at_index)
    after_sell_quantity = before_sell_quantity - sell_quantity
    if after_sell_quantity == 0: # to avoid negative zeros
        return before_sell_quantity, 0

    return before_sell_quantity, after_sell_quantity


# get the filename and the year from the user
if len(sys.argv) != 3:
    print("USE: python revolut_calculator.py <csv-file> <year>")
    exit(3)
file = sys.argv[1]
year = int(sys.argv[2])

# read the excel file
data = pd.read_csv(file, parse_dates=["Date"]) 

# check for unsupported activity types
supported_activities = ["BUY", "SELL", "DIVIDEND", "STOCK SPLIT", "CASH TOP-UP", "CASH WITHDRAWAL", "CUSTODY_FEE"]
file_activities = list(set(data["Type"]))
if any([(act not in supported_activities) for act in file_activities]):
    unsupported_activities = list(set(file_activities) - set(supported_activities))
    print("[X] The file contains unsupported activity types: " + ", ".join(unsupported_activities))
    print("[>] Supported activity types: " + ", ".join(supported_activities))
    exit(2)

# select sells
selected_columns = ["Date", "Ticker", "Quantity", "Total Amount"]
sell = data[(data["Type"] == "SELL") & (data["Date"].dt.year == year)][selected_columns]

# get remaining quantities
pre_post = [get_pre_and_post_quantities(data, i) for i in sell.index]
sell["Quantity before"] = [x[0] for x in pre_post]
sell["Quantity after"] = [x[1] for x in pre_post]

# get sell profits
sell["Profit"] = [get_sell_profit(data, i) for i in sell.index]

# get dividents 
dividend_selected_columns = ["Date", "Ticker", "Total Amount"]
dividend = data[(data["Type"] == "DIVIDEND") & (data["Date"].dt.year == year)][dividend_selected_columns]

# get results
sell_profit = sell["Profit"].sum()
dividend_sum = dividend["Total Amount"].sum()

# show the results
sell.to_csv("results_sell.csv")
print("Sells :")
print(sell) 
print("=> Profit : " + "{:.2f}".format(sell_profit) + " $")
print()

dividend.to_csv("results_dividend.csv")
print("Dividends :")
print(dividend) 
print("=> Sum : " + "{:.2f}".format(dividend_sum) + " $")
print()
 
print("Total profit: " + "{:.2f}".format(sell_profit + dividend_sum) + " $")
print()
