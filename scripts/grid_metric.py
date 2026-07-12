"""
parche_v31.py -- Correcciones para test_marco_paris4_v3.py  (v3 -> v3.1)

Dos problemas encontrados al verificar v3 sobre la superficie de Hao (129 x 13 mm):

(1) INTERLINEA GLOBAL INVALIDA. Con 13 mm de alto solo caben ~3 ciclos de
    interlinea: los "picos" del espectro Y son los bins k=3,4,5,10 de la altura
    (13.3/3 = 4.43 mm, 13.3/4 = 3.33, ...). El 4.45 mm detectado es un artefacto
    de resolucion. Ademas las lineas de columnas distintas no estan alineadas
    entre si, asi que la proyeccion Y de la tira completa destruye la
    periodicidad aunque hubiera resolucion.
    -> La interlinea se mide en el dominio ESPACIAL y POR COLUMNA:
       centros de linea como maximos locales del perfil, mediana de separaciones.

(2) COMPONENTES SUB-RESUELTAS EN EL BARRIDO. Ventana de 30 x 8 mm:
       letras  4.16 mm -> 7.2 ciclos  OK
       lineas  ~3-4 mm -> ~2 ciclos   NO medible
       columna 43 mm   -> 0.7 ciclos  NO medible
    -> Regla de gating: una componente solo entra en el score de una ventana si
       la ventana contiene >= MIN_CICLOS de su periodo. Con ventanas 30x8 solo
       'letras' califica; 'columna' se evalua globalmente (129 mm -> 3 ciclos,
       justo en el limite) y 'lineas' por columna con la funcion de abajo.

Uso: copia estas funciones dentro de test_marco_paris4_v3.py sustituyendo
     score_estructural(), y llama a interlinea_por_columnas() en la calibracion
     en lugar de detectar 'lineas' por FFT global.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

MIN_CICLOS = 3.0   # ciclos minimos del periodo objetivo dentro de la ventana


def interlinea_local(win, pixel_mm, p_min=2.0, p_max=8.0):
    """Interlinea por deteccion espacial de centros de linea en una ventana.
    Devuelve lista de separaciones [mm] (puede ser vacia)."""
    prof = win.sum(axis=1)
    if prof.std() < 1e-6:
        return []
    base = gaussian_filter1d(prof, sigma=max(3, int(p_max / pixel_mm)))
    prof2 = gaussian_filter1d(prof - base, sigma=max(1, int(0.25 / pixel_mm)))
    peaks, _ = find_peaks(prof2, distance=int(p_min / pixel_mm),
                          prominence=prof2.std() * 0.4)
    if len(peaks) < 2:
        return []
    sp = np.diff(peaks) * pixel_mm
    return list(sp[(sp >= p_min) & (sp <= p_max)])


def interlinea_por_columnas(arr, pixel_mm, ancho_col_mm=20.0, paso_mm=10.0):
    """Barre ventanas del ancho de una columna y agrega la interlinea local.
    Devuelve (mediana_mm, iqr, n_gaps). La dispersion ES parte del resultado:
    en tiras de ~13 mm la incertidumbre es grande y debe informarse."""
    W = arr.shape[1]
    win_w = int(ancho_col_mm / pixel_mm)
    paso = int(paso_mm / pixel_mm)
    todas = []
    for x0 in range(0, max(1, W - win_w), paso):
        todas += interlinea_local(arr[:, x0:x0 + win_w], pixel_mm)
    if len(todas) < 3:
        return None, None, len(todas)
    todas = np.array(todas)
    q1, q3 = np.percentile(todas, [25, 75])
    return float(np.median(todas)), (float(q1), float(q3)), len(todas)


def _prominencia_pico(senal, pixel_mm, p_obj, tol=0.20):
    """Igual que en v3 (sin cambios): prominencia del pico esperado sobre el
    fondo local del espectro."""
    if p_obj is None or len(senal) < 16:
        return 0.0
    s = senal - gaussian_filter1d(senal, sigma=max(2, len(senal) / 10))
    s = s * np.hanning(len(s))
    fft = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide='ignore'):
        per = np.where(freq > 0, 1.0 / freq, np.inf)
    m_pico = (per >= p_obj * (1 - tol)) & (per <= p_obj * (1 + tol))
    if not m_pico.any():
        return 0.0
    h_pico = fft[m_pico].max()
    m_fondo = ((per >= p_obj * (1 - 3 * tol)) & (per <= p_obj * (1 + 3 * tol)) & ~m_pico)
    if not m_fondo.any() or h_pico == 0:
        return 0.0
    h_fondo = np.median(fft[m_fondo]) + 1e-9
    return float(max(0.0, (h_pico - h_fondo) / h_fondo))


def score_estructural_v31(ventana, pixel_mm, periodos, min_ciclos=MIN_CICLOS,
                          devolver_detalle=False):
    """Score con GATING por ciclos: cada componente entra solo si la extension
    de la ventana en su eje contiene >= min_ciclos de su periodo.
    Combina las componentes calificadas por media geometrica; si ninguna
    califica devuelve 0 (y con devolver_detalle=True puedes ver por que)."""
    if ventana.size == 0:
        return (0.0, {}) if devolver_detalle else 0.0
    h_mm = ventana.shape[0] * pixel_mm
    w_mm = ventana.shape[1] * pixel_mm
    pY = ventana.sum(axis=1) - ventana.sum(axis=1).mean()
    pX = ventana.sum(axis=0) - ventana.sum(axis=0).mean()

    candidatos = {
        'lineas':  (periodos.get('lineas'),  pY, h_mm),
        'letras':  (periodos.get('letras'),  pX, w_mm),
        'columna': (periodos.get('columna'), pX, w_mm),
    }
    valores, detalle = [], {}
    for nombre, (p_obj, perfil, ext_mm) in candidatos.items():
        if p_obj is None:
            detalle[nombre] = ('sin periodo', None)
            continue
        ciclos = ext_mm / p_obj
        if ciclos < min_ciclos:
            detalle[nombre] = (f'gated ({ciclos:.1f} ciclos < {min_ciclos})', None)
            continue
        v = _prominencia_pico(perfil, pixel_mm, p_obj)
        detalle[nombre] = (f'{ciclos:.1f} ciclos', v)
        valores.append(v)

    if not valores:
        score = 0.0
    else:
        score = float(np.exp(np.mean(np.log(np.array(valores) + 0.01))))
    return (score, detalle) if devolver_detalle else score


if __name__ == "__main__":
    # autotest del gating con los parametros de v3 (ventana 30 x 8 mm)
    periodos = {'lineas': 3.0, 'letras': 4.16, 'columna': 43.0}
    pixel_mm = 0.0161
    win = np.random.rand(int(8 / pixel_mm), int(30 / pixel_mm))
    s, det = score_estructural_v31(win, pixel_mm, periodos, devolver_detalle=True)
    print("Gating con ventana 30 x 8 mm:")
    for k, (estado, v) in det.items():
        print(f"  {k:8s}: {estado}" + (f"  prominencia={v:.3f}" if v is not None else ""))
    print(f"  score = {s:.3f}")
