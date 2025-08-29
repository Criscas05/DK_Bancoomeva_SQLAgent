# from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union
import uuid

import pytz


class TimeManager:
    """
    Utilidades para manejo de fechas y generación de IDs únicos.
    """

    @staticmethod
    def current_time(timezone:str ="America/Bogota", to_str: bool =False, to_ymd:bool=False) -> Union[str, datetime]:
        """
        Retorna la hora actual en una zona horaria específica.

        Args:
            timezone (str): Zona horaria a usar.
            to_str (bool): Si se debe retornar como string.
            to_ymd (bool): Si se debe formatear como YYYYMMDD.

        Returns:
            Union[str, datetime]: Hora actual como string o datetime.
        """
        if not isinstance(to_str, bool):
            raise TypeError("El argumento 'to_str' debe ser booleano (True o False)")

        colombia_tz = pytz.timezone(timezone)
        current_time = datetime.now(colombia_tz).replace(tzinfo=None) #.isoformat(timespec='microseconds')

        if to_str and to_ymd:
            return current_time.strftime("%Y%m%d")
        elif to_str:
            return current_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return current_time


    @staticmethod
    def generate_timestamp_uuid_id() -> str:
        """
        Genera un identificador único basado en la fecha y un UUID.

        Returns:
            str: ID generado.
        """
        str_now = TimeManager.current_time(to_str=True, to_ymd=True)
        uuid_id = str(uuid.uuid4())
        chat_id = f'{str_now}-{uuid_id}'
        return chat_id


