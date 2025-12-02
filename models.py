class Cita:
    def __init__(self, dia, hora, ocupada=False):
        self.dia = dia.lower()
        self.hora = hora
        self.ocupada = ocupada

    def __repr__(self):
        return f"Cita(dia={self.dia}, hora={self.hora}, ocupada={self.ocupada})"


class Doctor:
    def __init__(self, id, nombre, especialidad, citas=None):
        self.id = id
        self.nombre = nombre
        self.especialidad = especialidad
        self.citas = citas or []

    def get_citas_disponibles(self):
        return [c for c in self.citas if not c.ocupada]

    def __repr__(self):
        return f"Doctor(id={self.id}, nombre={self.nombre}, especialidad={self.especialidad})"
