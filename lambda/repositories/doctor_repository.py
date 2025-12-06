from models.cita import Cita
from models.doctor import Doctor

class DoctorRepository:
    """
    REPOSITORY PATTERN: Abstrae el acceso a datos de doctores
    Permite cambiar la fuente de datos sin afectar la lógica de negocio
    """
    def __init__(self):
        self._doctores = self._init_doctores()
        self._aliases = self._init_aliases()
    
    def _init_doctores(self):
        """Inicializa los datos de doctores (podría venir de DB)"""
        return {
            "ramirez": Doctor(
                id="ramirez",
                nombre="Dra. Ramírez",
                especialidad="Pediatría",
                citas=[
                    Cita("lunes", "1:00"),
                    Cita("lunes", "2:00"),
                    Cita("miércoles", "2:00"),
                ],
            ),
            "gomez": Doctor(
                id="gomez",
                nombre="Dr. Gómez",
                especialidad="Cardiología",
                citas=[
                    Cita("lunes", "2:00"),
                    Cita("miércoles", "3:00"),
                ],
            ),
            "hernandez": Doctor(
                id="hernandez",
                nombre="Dr. Hernández",
                especialidad="Dermatología",
                citas=[
                    Cita("lunes", "4:00"),
                    Cita("miércoles", "2:00"),
                ],
            ),
        }
    
    def _init_aliases(self):
        """Inicializa los alias de doctores"""
        return {
            "dra ramirez": "ramirez",
            "dra. ramirez": "ramirez",
            "dr ramirez": "ramirez",
            "dr. ramirez": "ramirez",
            "dr gomez": "gomez",
            "dr. gomez": "gomez",
            "dr hernandez": "hernandez",
            "dr. hernandez": "hernandez",
        }
    
    def find_by_id(self, doctor_id):
        """Busca un doctor por ID"""
        if not doctor_id:
            return None
        doctor_id = doctor_id.lower()
        return self._doctores.get(doctor_id)
    
    def find_by_name(self, nombre_doctor):
        """Busca un doctor por nombre (incluye aliases)"""
        if not nombre_doctor:
            return None
        
        nombre_doctor = nombre_doctor.lower()
        
        # Buscar directo
        if nombre_doctor in self._doctores:
            return self._doctores[nombre_doctor]
        
        # Buscar por alias
        if nombre_doctor in self._aliases:
            original_id = self._aliases[nombre_doctor]
            return self._doctores.get(original_id)
        
        return None
    
    def get_all_doctores(self):
        """Retorna todos los doctores"""
        return list(self._doctores.values())

