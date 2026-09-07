def normalize_sku(sku):
    return sku.strip().upper()


def reserve(stock, sku, quantity):
    key = normalize_sku(sku)
    if stock.get(key, 0) < quantity:
        return False
    stock[key] -= quantity
    return True


def unrelated_label(name):
    return name[0].upper() + name[1:]
