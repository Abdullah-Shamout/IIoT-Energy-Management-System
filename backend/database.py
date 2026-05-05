import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import config

class Database:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            1,
            10,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )

    def get_connection(self):
        return self.pool.getconn()

    def release_connection(self, conn):
        self.pool.putconn(conn)

    def execute_query(self, query, params=None, fetch=True):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                    return result
                conn.commit()
                return None
        finally:
            self.release_connection(conn)

    def execute_one(self, query, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result
        finally:
            self.release_connection(conn)

    def insert_sensor_reading(self, device_id, voltage, current, power):
        query = """
            INSERT INTO sensor_readings (iot_device_id, reading_time, voltage, current, power)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        self.execute_query(query, (device_id, voltage, current, power), fetch=False)

    def get_all_devices(self):
        query = "SELECT * FROM iot_devices ORDER BY id"
        return self.execute_query(query)

    def get_device(self, device_id):
        query = "SELECT * FROM iot_devices WHERE id = %s"
        return self.execute_one(query, (device_id,))

    def update_device_status(self, device_id, status):
        query = "UPDATE iot_devices SET device_status = %s WHERE id = %s"
        self.execute_query(query, (status, device_id), fetch=False)

    def update_device_intensity(self, device_id, intensity):
        query = "UPDATE iot_devices SET device_intensity = %s WHERE id = %s"
        self.execute_query(query, (intensity, device_id), fetch=False)

    def update_device_total_consumption(self, device_id, consumption):
        query = "UPDATE iot_devices SET device_total_consumption = %s WHERE id = %s"
        self.execute_query(query, (consumption, device_id), fetch=False)

    def get_system_config(self):
        query = "SELECT * FROM system_configuration WHERE id = 1"
        return self.execute_one(query)

    def update_total_consumption(self, consumption):
        query = "UPDATE system_configuration SET total_consumption = %s WHERE id = 1"
        self.execute_query(query, (consumption,), fetch=False)

    def update_energy_budget(self, budget):
        query = "UPDATE system_configuration SET energy_budget = %s WHERE id = 1"
        self.execute_query(query, (budget,), fetch=False)

    def get_recent_readings(self, device_id=None, hours=24):
        if device_id:
            query = """
                SELECT reading_time, voltage, current, power
                FROM sensor_readings
                WHERE iot_device_id = %s
                AND reading_time >= NOW() - INTERVAL '%s hours'
                ORDER BY reading_time ASC
            """
            return self.execute_query(query, (device_id, hours))
        else:
            query = """
                SELECT time_bucket('30 seconds', reading_time) as reading_time, 
                       SUM(power) as total_power
                FROM sensor_readings
                WHERE reading_time >= NOW() - INTERVAL '%s hours'
                GROUP BY time_bucket('30 seconds', reading_time)
                ORDER BY reading_time ASC
            """
            return self.execute_query(query, (hours,))

db = Database()
