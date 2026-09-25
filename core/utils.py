def observatorio_del_usuario(user):
    """
    Devuelve el Observatorio al que está ligado el usuario (a través de su
    PerfilUsuario), o None si es anónimo, o si es un usuario de
    coordinación sin observatorio asignado (ve/crea sin acotar).
    """
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return None
    return perfil.observatorio
