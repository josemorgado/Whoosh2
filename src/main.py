#encoding:utf-8

from bs4 import BeautifulSoup
import urllib.request
from tkinter import *
from tkinter import messagebox
import re, shutil
from whoosh.index import create_in,open_dir
from whoosh.fields import Schema, TEXT, NUMERIC, KEYWORD, ID
from whoosh.qparser import QueryParser

PAGINAS = 4  #nÃºmero de pÃ¡ginas

# lineas para evitar error SSL
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context

def cargar():
    respuesta = messagebox.askyesno(title="Confirmar",message="Esta seguro que quiere recargar los datos. \nEsta operaciÃ³n puede ser lenta")
    if respuesta:
        almacenar_datos()
        
def extraer_juegos():
    lista=[]
    
    for p in range(1,PAGINAS+1):
        url="https://zacatrus.es/juegos-de-mesa.html?p="+str(p)
        f = urllib.request.urlopen(url)
        s = BeautifulSoup(f,"lxml")      
        
        l = s.ol.find_all("div", class_= "product-item-details")

        for i in l:
            titulo = i.a.string.strip()
            precio = re.compile('\d+,\d+').search(i.find("span", class_="price").string.strip()).group()
            precio = float(precio.replace(',','.'))
            
            f1 = urllib.request.urlopen(i.a['href'])
            j = BeautifulSoup(f1,"lxml")
          
            t = j.find("div", class_="additional-attributes")       
            if t :#tienen alguna/s de las caracterÃ­sticas adicionales
                temcom = t.find("div", class_="trs")
                tematica = temcom.find("div", attrs={"data-th":"TemÃ¡tica"})
                if tematica:
                    tematica = tematica.string.strip().lower()
                else:
                    tematica = "Desconocida"
                complejidad = temcom.find("div",attrs={"data-th":"Complejidad"})
                if complejidad:
                    complejidad = complejidad.string.strip()
                else:
                    complejidad = "Desconocida"
                jugadores = temcom.find("div",attrs={"data-th":"NÃºm. jugadores"})
                if jugadores:
                    jugadores = jugadores.string.strip()
                else:
                    jugadores = "Desconocida"
            else: #no tienen caracterÃ­sticas adicionales
                tematica = "Desconocida"
                complejidad = "Desconocida"
                jugadores="Desconocida"
            
            detalles=""
            d = j.find("div", class_="product info detailed")       
            if d :#si hay detalles
                d1 = d.find("div",class_="product attribute description")
                if d1:
                    detalles = d1.find("div",class_="value")
                    if detalles.div:
                        detalles = detalles.div
                    detalles = " ".join(list(detalles.stripped_strings))
                    #tambien se podria usar: detalles = detalles.get_text()
                      
            lista.append((titulo,precio,tematica,complejidad,jugadores,detalles))
        
    return lista


def imprimir_lista(cursor):
    v = Toplevel()
    v.title("JUEGOS DE MESA DE ZACATRUS")
    sc = Scrollbar(v)
    sc.pack(side=RIGHT, fill=Y)
    lb = Listbox(v, width = 150, yscrollcommand=sc.set)
    for row in cursor:
        lb.insert(END,row['titulo'])
        lb.insert(END,"    Precio: "+ str(row['precio']) + " â‚¬")
        lb.insert(END,"    TemÃ¡ticas: "+ row['tematicas'])
        lb.insert(END,"    Complejidad: "+ row['complejidad'])
        lb.insert(END,"    Jugadores: "+ row['jugadores'])
        lb.insert(END,"\n\n")
    lb.pack(side=LEFT,fill=BOTH)
    sc.config(command = lb.yview)

 
def almacenar_datos():
    #define el esquema de la informaciÃ³n
    schem = Schema(titulo=TEXT(stored=True,phrase=False), precio=NUMERIC(stored=True,numtype=float), tematicas=KEYWORD(stored=True,commas=True,lowercase=True), complejidad=ID(stored=True), jugadores=KEYWORD(stored=True,commas=True), detalles=TEXT)
    
    #eliminamos el directorio del Ã­ndice, si existe
    if os.path.exists("Index"):
        shutil.rmtree("Index")
    os.mkdir("Index")
    
    #creamos el Ã­ndice
    ix = create_in("Index", schema=schem)
    #creamos un writer para poder aÃ±adir documentos al indice
    writer = ix.writer()
    i=0
    lista=extraer_juegos()
    for j in lista:
        #aÃ±ade cada juego de la lista al Ã­ndice
        writer.add_document(titulo=str(j[0]), precio=float(str(j[1])), tematicas=str(j[2]), complejidad=str(j[3]), jugadores=str(j[4]), detalles=str(j[5]))    
        i+=1
    writer.commit()
    messagebox.showinfo("Fin de indexado", "Se han indexado "+str(i)+ " juegos")          

 
# permite buscar los juegos por una "temÃ¡tica"
def buscar_tematicas():
    def mostrar_lista(event):    
        with ix.searcher() as searcher:
            entrada = str(en.get().lower())
            #se busca como una frase porque hay temÃ¡ticas con varias palabras
            query = QueryParser("tematicas", ix.schema).parse('"'+entrada+'"')
            results = searcher.search(query,limit=None)
            imprimir_lista(results)
    
    
    v = Toplevel()
    v.title("BÃºsqueda por TemÃ¡tica")
    l = Label(v, text="Seleccione temÃ¡tica a buscar:")
    l.pack(side=LEFT)
    
    ix=open_dir("Index")      
    with ix.searcher() as searcher:
        #lista de todas las temÃ¡ticas disponibles en el campo de temÃ¡ticas
        lista_tematicas = [i.decode('utf-8') for i in searcher.lexicon('tematicas')]
    
    en = Spinbox(v, values=lista_tematicas, state="readonly")
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)

 
# permite buscar frases en los "detalles" de los juegos 
def buscar_detalles():
    def mostrar_lista(event):
        ix=open_dir("Index")
        with ix.searcher() as searcher:
            query = QueryParser("detalles", ix.schema).parse('"'+str(en.get())+'"')
            results = searcher.search(query,limit=10) #sÃ³lo devuelve los 10 primeros
            imprimir_lista(results)
    
    v = Toplevel()
    v.title("BÃºsqueda por Detalles")
    l = Label(v, text="Introduzca la frase a buscar:")
    l.pack(side=LEFT)
    en = Entry(v, width=75)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)
        

# permite buscar juegos hasta un precio
def buscar_precio():
    def mostrar_lista(event):
        if not re.match('\d+\.\d+', en.get().strip()):
            messagebox.showinfo("ERROR", "Formato incorrecto (ddd.ddd)")
            return
        ix=open_dir("Index")
        with ix.searcher() as searcher:
            query = QueryParser("precio", ix.schema).parse('[TO '+str(en.get().strip())+'}')
            results = searcher.search(query,limit=None) 
            imprimir_lista(results)
    
    v = Toplevel()
    v.title("BÃºsqueda por Precio")
    l = Label(v, text="Introduzca el precio mÃ¡ximo:")
    l.pack(side=LEFT)
    en = Entry(v)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)

# permite buscar juegos para un determinado nÃºmero de jugadores
def buscar_jugadores():
    def mostrar_lista(event):
        if not re.match('\d+', en.get().strip()):
            messagebox.showinfo("ERROR", "Formato incorrecto (dd)")
            return
        ix=open_dir("Index")
        with ix.searcher() as searcher:
            query = QueryParser("jugadores", ix.schema).parse(str(en.get().strip()))
            results = searcher.search(query,limit=None)
            imprimir_lista(results)
    
    v = Toplevel()
    v.title("BÃºsqueda por Jugadores")
    l = Label(v, text="Introduzca el nÃºmero de jugadores:")
    l.pack(side=LEFT)
    en = Entry(v)
    en.bind("<Return>", mostrar_lista)
    en.pack(side=LEFT)


def ventana_principal():       
    root = Tk()
    root.geometry("150x100")

    menubar = Menu(root)
    
    datosmenu = Menu(menubar, tearoff=0)
    datosmenu.add_command(label="Cargar", command=cargar)
    datosmenu.add_separator()   
    datosmenu.add_command(label="Salir", command=root.quit)
    
    menubar.add_cascade(label="Datos", menu=datosmenu)
    
    buscarmenu = Menu(menubar, tearoff=0)
    buscarmenu.add_command(label="Detalles", command=buscar_detalles)
    buscarmenu.add_command(label="TemÃ¡ticas", command=buscar_tematicas)
    buscarmenu.add_command(label="Precio", command=buscar_precio)
    buscarmenu.add_command(label="Jugadores", command=buscar_jugadores)
    
    menubar.add_cascade(label="Buscar", menu=buscarmenu)
        
    root.config(menu=menubar)
    root.mainloop()

    

if __name__ == "__main__":
    ventana_principal()