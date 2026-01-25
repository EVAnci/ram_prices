import requests
from statistics import median, std

url_catalog = 'https://static.compragamer.com/armado_pc_caracteristicas'
url_products = 'https://static.compragamer.com/productos'

def clean_mem(mem):
    unused_keys = ['disipador','sodimm','w','slot','activo','latencia_cl','disipacion_alta','es_cudimm','marca','voltaje']
    for key in unused_keys:
        mem.pop(key)

def get_price():
    catalog = requests.get(url_catalog)
    catalog_data = catalog.json()
    mems = catalog_data.get('mem')

    products = requests.get(url_products)
    products_data = products.json()
    
    tempmem = mems.copy()
    product_mems = []
    for product in products_data:
        if len(tempmem)==0:
            break
        i = 0
        for mem in tempmem:
            if product.get('id_producto') == mem.get('id_producto'):
                tempmem.pop(i)
                product_mems.append(product)
            i += 1
    
    ddr416 = []
    ddr48 = []
    ddr516 = []
    for mem in mems:
        clean_mem(mem) # return void. Here mem is passed by reference
        for product in product_mems:
            if mem.get('id_producto') == product.get('id_producto'):
                mem['precio'] = product.get('precioEspecial')
                mem['nombre'] = product.get('nombre')
                tipo = mem.get('tipo')
                capacidad = mem.get('capacidad')
                if tipo == 'DDR4':
                    if capacidad == 16:
                        ddr416.append(mem)
                    elif capacidad == 8:
                        ddr48.append(mem)
                elif tipo == 'DDR5':
                    if capacidad == 16:
                        ddr516.append(mem)

    return ddr416,ddr48,ddr516

def compute_stats(mems):
    prices = []
    for mem in mems:
        prices.append(mem.get('precio'))
    

if __name__ == '__main__':
    ddr416,ddr48,ddr516 = get_price()
