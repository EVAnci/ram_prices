import requests
from statistics import median, stdev
from json import dumps, loads
from datetime import date

url_catalog = 'https://static.compragamer.com/armado_pc_caracteristicas'
url_products = 'https://static.compragamer.com/productos'

def clean_mem(mem, secondary=False):
    '''
    Clean the unused keys on a memory dictionary.

    Recieves a dictionary and remove hardcoded keys.
        Optionally recieves secondary, that uses 
        a secondary hardcoded list of unused keys.
    '''
    if secondary:
        unused_keys = [
                'precios_cuotas',
                'imagenes',
                'precioListaAnterior',
                'precioEspecialAnterior',
                'garantia',
                'garantia_oficial',
                'busca_en_ml',
                'precioEspecialCombo',
                'iva',
                'impuesto_interno_importacion',
                'precioListaCombo',
                'id_nivel_falla',
                'descripcion_falla',
                'tipo_falla',
                'promocion'
            ]
    else:
        unused_keys = [
                'disipador',
                'sodimm',
                'w',
                'slot',
                'activo',
                'latencia_cl',
                'disipacion_alta',
                'es_cudimm',
                'marca',
                'voltaje'
            ]

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
            # The number 15 is to get the DIMM type of memory. Remove if want DIMM and SODIMM. Use 47 if just SODIMM
            if mem.get('id_producto') == product.get('id_producto') and product.get('id_subcategoria') == 15:
                # This shows the complete list shown of the page catalog
                # clean_mem(product,True)
                # print(dumps(product,indent=2))
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

    return {'max':max(prices), 'min':min(prices), 'med':median(prices), 'std':round(stdev(prices),2)}
    

if __name__ == '__main__':
    ddr416,ddr48,ddr516 = get_price()

    stats = {}
    stats['timestamp'] = str(date.today())

    stats['DDR4 16GB'] = compute_stats(ddr416)
    stats['DDR4 8GB'] = compute_stats(ddr48)
    stats['DDR5 16GB'] = compute_stats(ddr516)

    print(f'[+] RAM prices (based in compragamer.com)\n{dumps(stats,indent=2)}')

    try:
        open('prices.log','x')
        print('[+] Log file created.')
    except:
        print('[+] Log file already exists.')

    today_was_analized = False
    with open('prices.log','r') as p:
        try:
            price_log = loads(p.read())
            if stats.get('timestamp') != price_log[-1].get('timestamp'):
                price_log.append(stats)
            else:
                today_was_analized = True
        except:
            price_log = []
            price_log.append(stats)

    if not today_was_analized:
        with open('prices.log','w') as p:
            p.write(dumps(price_log,indent=2))
        print('[+] Written on log successfuly.')
    else:
        print(f'[+] The prices of today: {stats.get("timestamp")} are already written.')

    print('[+] All done, Good Bye!')
