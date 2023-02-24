#!/usr/bin/env python3 

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist 
import os

from time import sleep
from tkinter import Tk, Label, Button, Frame, Entry, messagebox,filedialog
from turtle_bot_5.srv import SavePath, DoPath
from turtle_bot_5.msg import Float32MultiArray
import tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from threading import Thread
from matplotlib.ticker import AutoMinorLocator

fig, ax = plt.subplots(facecolor="#e5e5e5")

xdata, ydata = [],[] 
guardar_ruta = False
salir = False
cargar = False
directorio_guardar_ruta = ""
directorio_realizar_ruta = ""

class MinimalSubscriber(Node, Thread):
    def __init__(self):
        Thread.__init__(self)
        super().__init__('turtle_bot_interface')
        self.subscription = self.create_subscription(
            Twist,
            '/turtlebot_position',
            self.listener_callback,
            10)
        self.save_path_srv = self.create_client(SavePath, 'save_path')
        self.do_path_srv = self.create_client(DoPath, 'do_path')

    def listener_callback(self, msg):
        global guardar_ruta

        xdata.append(msg.linear.x)
        ydata.append(msg.linear.y)
        self.get_logger().info('xdata:: "%s"' % xdata)
        self.get_logger().info('ydata:: "%s"' % ydata)
        
        if(guardar_ruta):
            print(guardar_ruta)
            
    def get_save_path(self):
        self.future = self.save_path_srv.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def save_path(self, path):
        global directorio_guardar_ruta
        f = open(directorio_guardar_ruta,"w+")
        f.write(str(path.data[0])+'\n')
        f.write(str(path.data[1])+'\n')
        for i in range (2, len(path.data)):
            f.write(str(int(path.data[i]))+",")
            if (i==len(path.data)-1):
                f.write(str(int(path.data[i])))
        f.close()

    def do_path(self):
        self.req_do_path.name = directorio_realizar_ruta
        self.future = self.do_path_srv.call_async(self.req_do_path)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def run(self):
        global salir 
        global guardar_ruta
        global directorio_realizar_ruta
        global cargar

        while(not salir):
            rclpy.spin_once(self)
            print(directorio_realizar_ruta)
            print("-----------------------------------")
            print(directorio_guardar_ruta)
        
        if(cargar):
            while not self.do_path_srv.wait_for_service(timeout_sec=1.0):
                self.get_logger().info('Finding do path service')
            self.req_do_path = DoPath.Request()
            self.do_path()
            print("xdddddd")
            salir = False
            print(salir)

        while(not salir):
            rclpy.spin_once(self)
            print(directorio_realizar_ruta)
            print("-----------------------------------")

        if(guardar_ruta):
            while not self.save_path_srv.wait_for_service(timeout_sec=1.0):
                self.get_logger().info('Press Q in the teleop console')
            self.req = SavePath.Request()
            response = self.get_save_path()
            self.save_path(response.path)

        

            
        

class VentanaTurtleBot(Thread):

    def __init__(self, root, minimal_subscriber):
        # Configuración inicial root
        self.root = root
        self.minimal_subscriber = minimal_subscriber
        self.root.geometry("800x800")
        self.root.title("Interfaz TurtleBot")
        self.root.minsize(width=800, height=800)
        self.root.resizable(False, False)

        # Configuración frame 
        frame_top= Frame(self.root, bg='white', bd=3)
        frame_top.pack(fill='both')
        
        frame_buttton = Frame(self.root, bg='white', bd=3)
        frame_buttton.pack(expand=1, fill='both')   

        # Top   
        Label(frame_top, text="Nombre de la gráfica:",bg="white", font='Helvetica 12 bold').pack(pady=5, side='left', expand=1)
        titulo = tkinter.StringVar(self.root, value='')
        Entry(frame_top, textvariable=titulo, width=30).pack(pady=5, side='left', expand=1)
        Button(frame_top, text='Empezar', width=15, bg='white', fg='black', font='Helvetica 12 bold', command=lambda: self.init(titulo)).pack(pady=5, side='left', expand=1)
        Button(frame_top, text='Cargar ruta', width=15, bg='white', fg='black', font='Helvetica 12 bold', command= self.do_path).pack(pady=5, side='left', expand=1)

        # Center
        global canvas 
        canvas = FigureCanvasTkAgg(fig, master=frame_buttton)
        canvas.get_tk_widget().pack(padx=2, pady=2, expand=1, fill='both')

        # Bottom
        Button(frame_buttton, text='Detener', width=15, bg='white', fg='black', font='Helvetica 12 bold', command=self.detener).pack(pady=5, side='left', expand=1)
        Button(frame_buttton, text='Reanudar', width=15, bg='white', fg='black', font='Helvetica 12 bold', command=self.reanudar).pack(pady=5, side='left', expand=1)
        Button(frame_buttton, text='Guardar', width=15, bg='white', fg='black', font='Helvetica 12 bold', command=self.guardar).pack(pady=5, side='left', expand=1)
        Button(frame_buttton, text='Salir', width=15, bg='white', fg='black', font='Helvetica 12 bold', command=self.salir).pack(pady=5, side='left', expand=1)


        self.root.mainloop()



    def animate(self, i):
        line, = ax.plot(xdata, ydata, color='m', linewidth=3, markersize=1, markeredgecolor='m')
        return line,

    def init(self, titulo):
        global ani 
        global guardar_ruta
        global directorio_guardar_ruta

        guardar_ruta = messagebox.askyesnocancel(message="¿Desea guardar la trayectoria del robot?", title="Interfaz TurtleBot")
        if guardar_ruta:
            directorio_guardar_ruta = filedialog.asksaveasfilename()
            print(directorio_guardar_ruta)

        plt.title(titulo.get(), color='black', size=16)
        plt.xlabel("Posición x [m]", fontsize=12)
        plt.ylabel("Posición y [m]", fontsize=12)
        # Give plot a balck background like ggplot.
        ax.set_facecolor('#000000')
        # Remove border around plot.
        [ax.spines[side].set_visible(False) for side in ax.spines]
        # Style the grid.
        ax.grid(which='major', color='white', linewidth=1.2)
        ax.grid(which='minor', color='white', linewidth=0.6)
        # Show the minor ticks and grid.
        ax.minorticks_on()
        # Now hide the minor ticks (but leave the gridlines).
        ax.tick_params(which='minor', bottom=False, left=False)
        # Only show minor gridlines once in between major gridlines.
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.set_xlim(-2.3, 2.3)
        ax.set_ylim(-2.3, 2.3)
        ani = animation.FuncAnimation(fig, self.animate, interval=20, blit=True, save_count=10)
        canvas.draw()

    def guardar(self):
        global salir 
        global guardar_ruta

        salir = messagebox.showinfo(message="Recuerda presionar Q en la consola del teleop", title="Título")
        for item in canvas.get_tk_widget().find_all():
            canvas.get_tk_widget().delete(item)
        plt.plot(xdata, ydata, color='m', linewidth=3, markersize=1, markeredgecolor='m')
        plt.show()

        self.salir()

    def do_path(self):
        global directorio_realizar_ruta
        global cargar 
        global salir 

        file = filedialog.askopenfilename()
        # Split the filepath to get the directory
        directorio_realizar_ruta = os.path.split(file)[0]+"/"+os.path.split(file)[1]
        salir = True
        cargar = True

    def salir(self):
        # Destroy all
        self.root.destroy()
        self.minimal_subscriber.destroy_node()
        rclpy.shutdown()

    def detener(self):
        ani.event_source.stop()

    def reanudar(self):
        ani.event_source.start()

def main(args=None):
    rclpy.init(args=args)

    # Thread encargado de la interfaz

    # Proceso principal encargado de recibir las posiciones "(x, y)"
    minimal_subscriber= MinimalSubscriber()
    minimal_subscriber.start()

    root = Tk()
    thread_plot = VentanaTurtleBot(root, minimal_subscriber)

    

    
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)

if __name__ == '__main__':
    main()

