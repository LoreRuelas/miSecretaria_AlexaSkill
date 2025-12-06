class Doctor:
    """Modelo de dominio para un doctor"""
    def __init__(self, id, nombre, especialidad, citas=None):
        self.id = id
        self.nombre = nombre
        self.especialidad = especialidad
        self.citas = citas or []
    
    def get_citas_disponibles(self):
        """Retorna lista de citas disponibles"""
        return [c for c in self.citas if not c.ocupada]
    
    def get_citas_ocupadas(self):
        """Retorna lista de citas ocupadas"""
        return [c for c in self.citas if c.ocupada]
    
    def buscar_cita(self, dia, hora):
        """Busca una cita específica por día y hora"""
        for cita in self.citas:
            if cita.dia == dia and cita.hora == hora:
                return cita
        return None
    
    def __repr__(self):
        return f"Doctor(id={self.id}, nombre={self.nombre}, especialidad={self.especialidad})"

