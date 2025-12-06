class CitasService:
    """
    FACADE: Proporciona una interfaz simplificada para operaciones de citas
    Coordina las operaciones entre repository y modelos de dominio
    """
    def __init__(self, doctor_repository):
        self.doctor_repository = doctor_repository
    
    def buscar_doctor(self, nombre_doctor):
        """Busca un doctor por nombre"""
        return self.doctor_repository.find_by_name(nombre_doctor)
    
    def obtener_citas_disponibles(self, doctor_id):
        """Obtiene citas disponibles de un doctor"""
        doctor = self.doctor_repository.find_by_id(doctor_id)
        if not doctor:
            return []
        return doctor.get_citas_disponibles()
    
    def obtener_citas_ocupadas(self, doctor_id):
        """Obtiene citas ocupadas de un doctor"""
        doctor = self.doctor_repository.find_by_id(doctor_id)
        if not doctor:
            return []
        return doctor.get_citas_ocupadas()
    
    def agendar_cita(self, doctor_id, dia, hora):
        """Agenda una cita específica"""
        doctor = self.doctor_repository.find_by_id(doctor_id)
        if not doctor:
            return False
        
        cita = doctor.buscar_cita(dia, hora)
        if cita and not cita.ocupada:
            cita.marcar_ocupada()
            return True
        return False
    
    def cancelar_cita(self, doctor_id, dia, hora):
        """Cancela una cita específica"""
        doctor = self.doctor_repository.find_by_id(doctor_id)
        if not doctor:
            return False
        
        cita = doctor.buscar_cita(dia, hora)
        if cita and cita.ocupada:
            cita.liberar()
            return True
        return False
        
    def obtener_todos_doctores(self):
        """Obtiene todos los doctores disponibles"""
        return self.doctor_repository.get_all_doctores()