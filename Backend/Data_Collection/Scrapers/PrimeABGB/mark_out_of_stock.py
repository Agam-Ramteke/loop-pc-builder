from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['PC_Parts']
collections = ['Processors', 'GPUs', 'RAM', 'Storage', 'Motherboards', 'SMPS', 'Cabinets', 'CpuCoolers']
total = 0
for c in collections:
    res = db[c].update_many(
        {
            '$or': [
                {'price.discounted': None},
                {'price.discounted': ''},
                {'price.discounted': {'$exists': False}}
            ]
        },
        {'$set': {'out_of_stock': True, 'stock_status': 'Out of Stock'}}
    )
    total += res.modified_count
    print(f'{c}: {res.modified_count}')
print(f'Total: {total}')
