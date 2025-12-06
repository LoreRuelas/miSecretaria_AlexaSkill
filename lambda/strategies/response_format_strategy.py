from abc import ABC, abstractmethod

class ResponseFormatStrategy(ABC):
    """
    STRATEGY PATTERN: Define una familia de algoritmos para formatear respuestas
    Permite cambiar el formato de respuesta sin modificar el handler
    """
    @abstractmethod
    def format(self, data):
        """Formatea los datos según la estrategia específica"""
        pass


class CitasDisponiblesFormatStrategy(ResponseFormatStrategy):
    """Estrategia para formatear lista de citas disponibles con letras"""
    
    def format(self, data):
        """
        data = {
            'doctor_nombre': str,
            'citas': [Cita, ...]
        }
        returns: {
            'speech': str,
            'opciones': dict {letra: (dia, hora)}
        }
        """
        doctor_nombre = data.get('doctor_nombre', '')
        citas = data.get('citas', [])
        
        if not citas:
            return {
                'speech': f"El doctor {doctor_nombre} no tiene citas disponibles.",
                'opciones': {}
            }
        
        opciones = {}
        letras = ["A", "B", "C", "D", "E", "F", "G", "H"]
        speak_list = ""
        
        for i, cita in enumerate(citas):
            letra = letras[i]
            opciones[letra] = (cita.dia, cita.hora)
            speak_list += f"Opción {letra}: {cita.dia} a las {cita.hora}. "
        
        speech = (
            f"Perfecto, estas son las citas disponibles con {doctor_nombre}: "
            f"{speak_list}Indique la opción que desea, por ejemplo diga: opción A."
        )
        
        return {
            'speech': speech,
            'opciones': opciones
        }


class CitasOcupadasFormatStrategy(ResponseFormatStrategy):
    """Estrategia para formatear cita ocupada (una sola)"""
    
    def format(self, data):
        """
        data = {
            'doctor_nombre': str,
            'citas': [Cita, ...]
        }
        returns: {
            'speech': str,
            'cita': (dia, hora) o None
        }
        """
        doctor_nombre = data.get('doctor_nombre', '')
        citas = data.get('citas', [])
        
        if not citas:
            return {
                'speech': f"No tienes ninguna cita agendada con {doctor_nombre}.",
                'cita': None
            }
        
        # Solo tomamos la primera cita (el usuario solo puede tener una)
        cita = citas[0]
        
        speech = (
            f"Tienes esta cita con {doctor_nombre}: "
            f"{cita.dia} a las {cita.hora}. "
            f"Para cancelarla di: sí quiero cancelar mi cita."
        )
        
        return {
            'speech': speech,
            'cita': (cita.dia, cita.hora)
        }


class ConfirmacionFormatStrategy(ResponseFormatStrategy):
    """Estrategia para formatear mensajes de confirmación"""
    
    def format(self, data):
        """
        data = {
            'tipo': 'agendar' | 'cancelar',
            'dia': str,
            'hora': str
        }
        """
        tipo = data.get('tipo', 'agendar')
        dia = data.get('dia', '')
        hora = data.get('hora', '')
        
        if tipo == 'agendar':
            speech = f"Cita agendada con éxito el {dia} a las {hora}. ¿Desea hacer algo más?"
        else:  # cancelar
            speech = f"La cita del {dia} a las {hora} ha sido cancelada. ¿Desea hacer algo más?"
        
        return {
            'speech': speech,
            'opciones': {}
        }
        
class ConsultarInfoFormatStrategy(ResponseFormatStrategy):
    """Estrategia para formatear información del doctor"""
    
    def format(self, data):
        """
        data = {
            'doctor': Doctor object
        }
        """
        doctor = data.get('doctor')
        
        if not doctor:
            return {
                'speech': "No encontré información de ese doctor."
            }
        
        citas_disponibles = doctor.get_citas_disponibles()
        citas_ocupadas = doctor.get_citas_ocupadas()
        
        speech = (
            f"{doctor.nombre} es especialista en {doctor.especialidad}. "
            f"Tiene {len(citas_disponibles)} citas disponibles "
            f"y {len(citas_ocupadas)} citas ocupadas."
        )
        
        return {
            'speech': speech
        }


class ListarDoctoresFormatStrategy(ResponseFormatStrategy):
    """Estrategia para formatear lista de doctores disponibles"""
    
    def format(self, data):
        """
        data = {
            'doctores': [Doctor, ...]
        }
        """
        doctores = data.get('doctores', [])
        
        if not doctores:
            return {
                'speech': "No hay doctores disponibles en este momento."
            }
        
        nombres = []
        for doc in doctores:
            nombres.append(f"{doc.nombre}, especialista en {doc.especialidad}")
        
        lista_doctores = "; ".join(nombres)
        
        speech = f"Tenemos los siguientes doctores disponibles: {lista_doctores}."
        
        return {
            'speech': speech
        }

