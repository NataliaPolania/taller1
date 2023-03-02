#!/usr/bin/env python3 

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist 
import sys
from turtle_bot_5.srv import DoPath
import time

data_loaded = False

class MinimalService(Node):
    
    def __init__(self):
        
        super().__init__('turtle_bot_player')
        self._do_path_srv = self.create_service(DoPath, 'do_path', self.do_path)
        self.publisher_ = self.create_publisher(Twist, 'turtlebot_cmdVel', 1) 
        timer_period = 2  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.movements = [] 
        self.i = 0

    def load_data(self, archivo):
        # Funcion encargada de abrir el archivo y obtener el vector de los movimientos y las velocidades lineal y angular
        global data_loaded

        f = open(archivo, "r")
        self.vel_lineal = float(f.readline())
        self.vel_angular = float(f.readline())
        for i in f.readline().split(sep=','):
            self.movements.append(i)
        data_loaded = True
    
    def do_path(self, request, response):
        # Función encargada por obtener la ruta del archivo .txt con los movimientos del robot
        
        print("Ruta:" + request.name)
        archivo = request.name
        self.load_data(archivo)
        return response

    def timer_callback(self):
        # Función encargada de crear el mensaje Twist y publicarlo en el tópico turtlebot_cmdVel
        
        global data_loaded
        print("searching data")
        while(data_loaded):
            for i in self.movements:
                linear = 0.0
                angular = 0.0

                if i == "4":
                    angular = self.vel_angular

                elif i == "3":
                    angular = -self.vel_angular

                elif i == "1":
                    linear = self.vel_lineal   

                elif i == "2":
                    linear = -self.vel_lineal

                if(angular!=0.0 or linear!=0.0):
                    print(i)
                    msg = Twist()
                    msg.angular.z = angular
                    msg.linear.x = linear
                    self.publisher_.publish(msg) 

                    msg.angular.z = 0.0
                    msg.linear.x = 0.0
                    self.publisher_.publish(msg)
                time.sleep(0.025)
            data_loaded = False
            print("Path finished")    

def main(args=None):
    rclpy.init(args=args)
    # Proceso principal encargado de ejecutar todo el proceso del player
    minimal_service = MinimalService()
    rclpy.spin(minimal_service)
    rclpy.shutdown()
    
if __name__ == '__main__':
    main()
