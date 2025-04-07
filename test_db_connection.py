#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

def test_connection():
    # Laden der Variablen aus der .env-Datei
    load_dotenv()

    host = os.getenv('MYSQL_HOST', 'localhost')
    user = os.getenv('MYSQL_USER', 'root')
    database = os.getenv('MYSQL_DATABASE', 'scilit2')
    port = os.getenv('MYSQL_PORT', 3306)
    
    # Passwort wird direkt aus der Umgebungsvariable bezogen
    password = os.getenv('MYSQL_PASSWORD', '')

    try:
        # Verbindung zur Datenbank herstellen
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        
        if connection.is_connected():
            print("Verbindung erfolgreich hergestellt!")
            # Informationen zum MySQL-Server abrufen
            server_info = connection.get_server_info()
            print("MySQL Server Version:", server_info)
            
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            current_db = cursor.fetchone()
            print("Aktuell verwendete Datenbank:", current_db[0])
    except Error as e:
        print("Fehler beim Verbinden zur MySQL-Datenbank:", e)
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL Verbindung wurde geschlossen.")

if __name__ == "__main__":
    test_connection()
