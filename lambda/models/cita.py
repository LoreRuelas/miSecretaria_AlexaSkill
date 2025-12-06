class Cita:
    """Modelo de dominio para una cita médica"""
    def __init__(self, dia, hora, ocupada=False):
        self.dia = dia.lower()
        self.hora = hora
        self.ocupada = ocupada
    
    def marcar_ocupada(self):
        """Marca la cita como ocupada"""
        self.ocupada = True
    
    def liberar(self):
        """Libera la cita"""
        self.ocupada = False
    
    def __repr__(self):
        return f"Cita(dia={self.dia}, hora={self.hora}, ocupada={self.ocupada})"
