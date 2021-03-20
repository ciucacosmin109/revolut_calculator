import sys
import pandas as pd

pd.options.display.float_format = "{:,.8f}".format
pd.options.display.max_rows = 50
pd.options.display.max_columns = 10
pd.options.display.width = 256


def get_buy_data(data, stock_code, at_index):
    buy = data[(data["Symbol / Description"] == stock_code) & (data.index < at_index)]
    filter_activities = ["BUY", "SELL", "SSO", "SSP"]
    buy = buy[buy["Activity Type"].isin(filter_activities)]

    buy_quantity = 0
    buy_amount = 0
    avg_buy_price = 0
    for i in buy.index:
        activity = buy["Activity Type"][i]
        if activity == "BUY" or activity == "SSP":
            buy_quantity += buy["Quantity"][i]
            buy_amount += buy["Amount"][i]

            if buy_quantity != 0:
                avg_buy_price = buy_amount / buy_quantity
        elif activity == "SELL":
            buy_quantity += buy["Quantity"][i]
            buy_amount = avg_buy_price * buy_quantity
            if buy_amount == 0:
                avg_buy_price = 0

    return avg_buy_price, buy_quantity, buy_amount


def get_sell_profit(data, at_index):
    sell_instance = data[data.index == at_index]
    stock_code = sell_instance["Symbol / Description"][at_index]
    sell_amount = sell_instance["Amount"][at_index]
    sell_quantity = sell_instance["Quantity"][at_index]

    avg_buy_price, buy_quantity, buy_amount = get_buy_data(data, stock_code, at_index)

    # check if there is a partial sell
    if buy_quantity > - sell_quantity: # sell_quantity is negative
        avg_buy_price = buy_amount / buy_quantity
        return sell_amount - sell_quantity * avg_buy_price
    else:
        return sell_amount + buy_amount # buy_amount is negative


def get_pre_and_post_quantities(data, at_index):
    sell_instance = data[data.index == at_index]
    stock_code = sell_instance["Symbol / Description"][at_index]
    sell_quantity = sell_instance["Quantity"][at_index]

    _, before_sell_quantity, _ = get_buy_data(data, stock_code, at_index)
    after_sell_quantity = before_sell_quantity + sell_quantity
    if after_sell_quantity == 0: # to avoid negative zeros
        return before_sell_quantity, 0

    return before_sell_quantity, after_sell_quantity


# get the filename and the year from the user
if len(sys.argv) != 3:
    print("USE: python revolut_calculator.py <excel-file> <year>")
    exit(3)
file = sys.argv[1]
year = int(sys.argv[2])

# read the excel file
data = pd.read_excel(file, skiprows=1, usecols="A:H", parse_dates=False)
data = data.drop(data[data["Trade Date"].isna()].index) # remove empty rows
data["Symbol / Description"] = [s.split(" ")[0] for s in data["Symbol / Description"]] # get only the stock codes

# check for unsupported activity types
supported_activities = ["BUY", "SELL", "CDEP", "CSD", "SSO", "SSP"]
xlsx_activities = list(set(data["Activity Type"]))
if any([(act not in supported_activities) for act in xlsx_activities]):
    unsupported_activities = list(set(xlsx_activities) - set(supported_activities))
    print("[X] The xlsx file contains unsupported activity types: " + ", ".join(unsupported_activities))
    print("[>] Supported activity types: " + ", ".join(supported_activities))
    exit(2)

# select columns for sells
selected_columns = ["Trade Date", "Symbol / Description", "Quantity", "Amount"]
sell = data[(data["Activity Type"] == "SELL") & (data["Trade Date"].dt.year == year)][selected_columns]

# get remaining quantities
pre_post = [get_pre_and_post_quantities(data, i) for i in sell.index]
sell["Quantity before"] = [x[0] for x in pre_post]
sell["Quantity after"] = [x[1] for x in pre_post]

# get sell profits
sell["Profit"] = [get_sell_profit(data, i) for i in sell.index]

# show the results
sell.to_excel("results.xlsx")
print(sell)
print()
print("Profit: " + "{:.2f}".format(sell["Profit"].sum()) + " $")
