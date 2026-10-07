/*
 * Filtros, indicadores y gráficos del tablero (público y privado).
 *
 * Cada página define antes window.TABLERO_CONFIG:
 *   obsInicial          id del observatorio con el que arranca el filtro (o null)
 *   bloquearTerritorio  true = departamento/municipio/observatorio quedan fijos
 *   periodoInicial      período con el que arranca (por defecto '12m'; '' = todo el tiempo)
 *   alActualizar(params) opcional: se llama con la cadena de filtros cada vez
 *                       que se recargan las cifras (el tablero privado lo usa
 *                       para refrescar su tabla de casos)
 */
(function () {
  const cfg = window.TABLERO_CONFIG || {};
  const obsInicial = cfg.obsInicial || null;
  const bloquearTerritorio = Boolean(cfg.bloquearTerritorio);

  const periodoInicial = cfg.periodoInicial === undefined ? '12m' : cfg.periodoInicial;

  // Verde institucional para barras y línea; categorías bien distinguibles para la dona.
  const paleta = ['#1D6D48', '#F5B82E', '#4F8FE0', '#DC3C44', '#7941A4', '#899194', '#E8892B', '#2BA5A0'];
  const COLOR_BARRAS = '#14603C';
  const COLOR_LINEA = '#1D6D48';
  const MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

  if (window.Chart) {
    Chart.defaults.font.family = '"Public Sans", -apple-system, sans-serif';
    Chart.defaults.color = '#3C4A43';
  }

  const $ = (id) => document.getElementById(id);
  const formatoNumero = (n) => Number(n || 0).toLocaleString('es-CO');

  let observatorios = [];
  let graficos = {};
  let peticionActual = 0;
  let ultimoResumen = null;

  // ---------------------------------------------------------------
  // Datos para los desplegables
  // ---------------------------------------------------------------
  async function obtenerTodasPaginas(url) {
    let resultados = [];
    while (url) {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (Array.isArray(data)) { resultados = resultados.concat(data); url = null; }
      else { resultados = resultados.concat(data.results || []); url = data.next; }
    }
    return resultados;
  }

  function llenarSelect(select, textoTodos, opciones, valorActual) {
    select.innerHTML = '';
    const todos = document.createElement('option');
    todos.value = '';
    todos.textContent = textoTodos;
    select.appendChild(todos);
    opciones.forEach(({ valor, texto }) => {
      const opt = document.createElement('option');
      opt.value = valor;
      opt.textContent = texto;
      select.appendChild(opt);
    });
    if (valorActual && opciones.some(o => String(o.valor) === String(valorActual))) {
      select.value = valorActual;
    }
  }

  const unicosOrdenados = (valores) =>
    [...new Set(valores.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));

  function llenarDepartamentos() {
    const deps = unicosOrdenados(observatorios.map(o => o.departamento));
    llenarSelect($('fDepartamento'), 'Todos', deps.map(d => ({ valor: d, texto: d })), $('fDepartamento').value);
  }

  function llenarMunicipios() {
    const dep = $('fDepartamento').value;
    const lista = observatorios.filter(o => !dep || o.departamento === dep);
    const muns = unicosOrdenados(lista.map(o => o.municipio));
    llenarSelect($('fMunicipio'), 'Todos', muns.map(m => ({ valor: m, texto: m })), $('fMunicipio').value);
  }

  function llenarObservatorios() {
    const dep = $('fDepartamento').value;
    const mun = $('fMunicipio').value;
    const lista = observatorios
      .filter(o => (!dep || o.departamento === dep) && (!mun || o.municipio === mun))
      .sort((a, b) => a.codigo.localeCompare(b.codigo, 'es'));
    llenarSelect($('fObservatorio'), 'Todos',
      lista.map(o => ({ valor: o.id, texto: `${o.codigo} - ${o.nombre}` })), $('fObservatorio').value);
  }

  function fijarTerritorioInicial() {
    const propio = observatorios.find(o => o.id === obsInicial);
    if (!propio) return;
    $('fDepartamento').value = propio.departamento || '';
    llenarMunicipios();
    $('fMunicipio').value = propio.municipio || '';
    llenarObservatorios();
    $('fObservatorio').value = String(propio.id);
  }

  async function cargarOpcionesDeFiltros() {
    const [obs, tipos] = await Promise.all([
      obtenerTodasPaginas('/api/observatorios/?activo=true'),
      obtenerTodasPaginas('/api/tipos-hecho/?activo=true'),
    ]);
    observatorios = obs;
    llenarDepartamentos();
    llenarMunicipios();
    llenarObservatorios();
    llenarSelect($('fTipoHecho'), 'Todos',
      tipos.map(t => ({ valor: t.id, texto: t.nombre })), '');

    if (obsInicial) fijarTerritorioInicial();
    if (bloquearTerritorio) {
      ['fDepartamento', 'fMunicipio', 'fObservatorio'].forEach(id => { $(id).disabled = true; });
    }
  }

  // ---------------------------------------------------------------
  // Período
  // ---------------------------------------------------------------
  const aISO = (f) =>
    `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, '0')}-${String(f.getDate()).padStart(2, '0')}`;

  function rangoDelPeriodo() {
    const hoy = new Date();
    const periodo = $('fPeriodo').value;
    if (periodo === '30d') {
      const d = new Date(hoy); d.setDate(d.getDate() - 30);
      return { desde: aISO(d), hasta: aISO(hoy) };
    }
    if (periodo === '3m' || periodo === '6m' || periodo === '12m') {
      const d = new Date(hoy); d.setMonth(d.getMonth() - parseInt(periodo, 10));
      return { desde: aISO(d), hasta: aISO(hoy) };
    }
    if (periodo === 'anio') {
      return { desde: `${hoy.getFullYear()}-01-01`, hasta: aISO(hoy) };
    }
    if (periodo === 'anio_anterior') {
      const a = hoy.getFullYear() - 1;
      return { desde: `${a}-01-01`, hasta: `${a}-12-31` };
    }
    if (periodo === 'personalizado') {
      return { desde: $('fDesde').value, hasta: $('fHasta').value };
    }
    return { desde: '', hasta: '' };
  }

  function actualizarCamposDeFecha() {
    const personalizado = $('fPeriodo').value === 'personalizado';
    $('filaFechas').hidden = !personalizado;
  }

  // ---------------------------------------------------------------
  // Consulta y dibujo
  // ---------------------------------------------------------------
  function construirParametros() {
    const p = new URLSearchParams();
    const { desde, hasta } = rangoDelPeriodo();
    if (desde) p.set('fecha_desde', desde);
    if (hasta) p.set('fecha_hasta', hasta);
    if ($('fDepartamento').value) p.set('departamento', $('fDepartamento').value);
    if ($('fMunicipio').value) p.set('municipio', $('fMunicipio').value);
    if ($('fObservatorio').value) p.set('observatorio', $('fObservatorio').value);
    if ($('fTipoHecho').value) p.set('tipo_hecho', $('fTipoHecho').value);
    return p;
  }

  function textoDeSelect(id) {
    const s = $(id);
    return s.value ? s.options[s.selectedIndex].textContent : '';
  }

  function hayFiltroTerritorial() {
    return ['fDepartamento', 'fMunicipio', 'fObservatorio'].some(id => $(id).value);
  }

  function hayOtrosFiltros() {
    return hayFiltroTerritorial() || Boolean($('fTipoHecho').value);
  }

  function actualizarResumenDeFiltros() {
    const partes = [];
    const periodo = $('fPeriodo').value;
    if (periodo && periodo !== periodoInicial && periodo !== 'personalizado') partes.push(textoDeSelect('fPeriodo'));
    if (periodo === 'personalizado') {
      const { desde, hasta } = rangoDelPeriodo();
      if (desde || hasta) partes.push(`${desde || 'inicio'} a ${hasta || 'hoy'}`);
    }
    ['fDepartamento', 'fMunicipio', 'fObservatorio', 'fTipoHecho'].forEach(id => {
      if ($(id).value) partes.push(textoDeSelect(id));
    });
    $('resumenFiltros').hidden = partes.length === 0;
    $('resumenFiltros').textContent = partes.length ? `Filtros aplicados: ${partes.join(' · ')}` : '';
  }

  function notaDelPeriodo() {
    const base = $('fPeriodo').value ? textoDeSelect('fPeriodo') : 'Cifra acumulada';
    return hayOtrosFiltros() ? `${base} · con filtros` : base;
  }

  function formatoFecha(iso) {
    if (!iso) return '—';
    const [a, m, d] = iso.split('-').map(Number);
    return `${String(d).padStart(2, '0')} ${MESES_CORTOS[m - 1].toLowerCase()} ${a}`;
  }

  // Escribe el valor de cada barra al final de la misma.
  const pluginValoresEnBarras = {
    id: 'valoresEnBarras',
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.font = '700 12px "Public Sans", sans-serif';
      ctx.fillStyle = '#1B2420';
      ctx.textBaseline = 'middle';
      chart.getDatasetMeta(0).data.forEach((barra, i) => {
        ctx.fillText(formatoNumero(chart.data.datasets[0].data[i]), barra.x + 6, barra.y);
      });
      ctx.restore();
    },
  };

  // Valor sobre cada punto de la línea.
  const pluginValoresEnLinea = {
    id: 'valoresEnLinea',
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.font = '700 11px "Public Sans", sans-serif';
      ctx.fillStyle = '#1B2420';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      chart.getDatasetMeta(0).data.forEach((punto, i) => {
        ctx.fillText(formatoNumero(chart.data.datasets[0].data[i]), punto.x, punto.y - 7);
      });
      ctx.restore();
    },
  };

  function dibujar(id, config) {
    if (graficos[id]) graficos[id].destroy();
    graficos[id] = new Chart($(id), config);
  }

  function quitarGrafico(id) {
    if (graficos[id]) { graficos[id].destroy(); delete graficos[id]; }
  }

  function mostrarGrafico(caja, sinDatos, hayDatos) {
    $(caja).hidden = !hayDatos;
    $(sinDatos).hidden = hayDatos;
  }

  const recortar = (t, n) => (t.length > n ? `${t.slice(0, n - 1).trimEnd()}…` : t);

  // Barras horizontales: por municipio o por observatorio, con "Top N".
  function dibujarBarras() {
    if (!ultimoResumen) return;
    const porObservatorio = document.querySelector('input[name="vistaBarras"]:checked').value === 'observatorio';
    $('tituloBarras').textContent = porObservatorio ? 'Casos por observatorio' : 'Casos por municipio';

    let labels, data;
    if (porObservatorio) {
      const s = ultimoResumen.por_observatorio;
      labels = s.labels.map((codigo, i) => [codigo, recortar((s.nombres || [])[i] || '', 28)]);
      data = s.data;
    } else {
      labels = ultimoResumen.por_municipio.labels;
      data = ultimoResumen.por_municipio.data;
    }
    const top = Number($('fTopBarras').value);
    if (top > 0) { labels = labels.slice(0, top); data = data.slice(0, top); }

    const hay = labels.length > 0;
    mostrarGrafico('cajaMunicipios', 'sinDatosMunicipios', hay);
    if (!hay) { quitarGrafico('gMunicipios'); return; }

    // Altura según la cantidad de barras, para que cada una se lea bien.
    $('cajaMunicipios').style.height = `${Math.max(310, labels.length * (porObservatorio ? 40 : 32) + 50)}px`;
    dibujar('gMunicipios', {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'Casos', data, backgroundColor: COLOR_BARRAS, borderRadius: 3, barThickness: 20 }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 34 } },
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#E6EAE4' } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      },
      plugins: [pluginValoresEnBarras],
    });
  }

  function dibujarTipoHecho(serie) {
    const hay = serie.labels.length > 0;
    mostrarGrafico('cajaTipoHecho', 'sinDatosTipoHecho', hay);
    if (!hay) { quitarGrafico('gTipoHecho'); return; }
    dibujar('gTipoHecho', {
      type: 'doughnut',
      data: {
        labels: serie.labels,
        datasets: [{ data: serie.data, backgroundColor: paleta, borderColor: '#fff', borderWidth: 2 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '36%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 8, boxHeight: 8, font: { size: 11 } },
          },
        },
      },
    });
  }

  function etiquetaMes(clave) {
    const [anio, mes] = clave.split('-').map(Number);
    return [MESES_CORTOS[mes - 1], String(anio)];
  }

  function dibujarMeses(serie) {
    const hay = serie.labels.length > 0;
    mostrarGrafico('cajaMeses', 'sinDatosMeses', hay);
    if (!hay) { quitarGrafico('gMeses'); return; }
    dibujar('gMeses', {
      type: 'line',
      data: {
        labels: serie.labels.map(etiquetaMes),
        datasets: [{
          label: 'Casos', data: serie.data, borderColor: COLOR_LINEA, borderWidth: 2.5,
          backgroundColor: 'rgba(29,109,72,.13)', fill: true, tension: 0.3,
          pointBackgroundColor: COLOR_LINEA, pointBorderColor: '#fff', pointBorderWidth: 1.5, pointRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 22, right: 8 } },
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: { beginAtZero: true, grace: '12%', ticks: { precision: 0 }, grid: { color: '#E6EAE4' } },
        },
      },
      plugins: [pluginValoresEnLinea],
    });
  }

  const ICONOS_POBLACION = {
    hombres: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2.4"/><path d="M8.5 21v-8.2a1.8 1.8 0 0 1 1.8-1.8h3.4a1.8 1.8 0 0 1 1.8 1.8V21"/><line x1="12" y1="15" x2="12" y2="21"/></svg>',
    mujeres: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2.4"/><path d="M12 10.5c-2 0-3 1.3-3.6 3.2L6.8 19h10.4l-1.6-5.3c-.6-1.9-1.6-3.2-3.6-3.2Z"/><line x1="10" y1="19" x2="10" y2="21.5"/><line x1="14" y1="19" x2="14" y2="21.5"/></svg>',
    nna: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="6.5" r="2"/><path d="M5 20v-6a3 3 0 0 1 6 0v6"/><circle cx="17" cy="9.5" r="1.7"/><path d="M14.5 20v-4.2a2.5 2.5 0 0 1 5 0V20"/></svg>',
    mayores: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="5" r="2.3"/><path d="M7.5 21v-7.5a2.5 2.5 0 0 1 5 0V21"/><path d="M15.5 11v10"/><path d="M13.5 11h2a2 2 0 0 1 2 2"/></svg>',
    familias: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="7" cy="6" r="2"/><circle cx="17" cy="6" r="2"/><circle cx="12" cy="11.5" r="1.6"/><path d="M3.5 20v-6a3.5 3.5 0 0 1 7 0v6"/><path d="M13.5 20v-6a3.5 3.5 0 0 1 7 0v6"/></svg>',
  };

  function dibujarPoblacion(p) {
    const personas = p.personas || 0;
    const items = [
      ['hombres', 'Hombres', p.hombres, '#2F7DE1', '#DAEBFB'],
      ['mujeres', 'Mujeres', p.mujeres, '#E0467C', '#FCDCE7'],
      ['nna', 'Niños, niñas y adolescentes (NNA)', p.ninos_adolescentes, '#E8892B', '#F8E2CB'],
      ['mayores', 'Adultos mayores', p.adultos_mayores, '#7B4FB0', '#E3D8F1'],
      ['familias', 'Familias', p.familias, '#1D6D48', '#DBEBE0'],
    ];
    $('filasPoblacion').innerHTML = items.map(([clave, etiqueta, valor, tono, tinte]) => {
      const pct = personas > 0 ? Math.min(100, Math.round((valor / personas) * 100)) : 0;
      return `
      <div class="poblacion__item" style="--tono:${tono};--tinte:${tinte}">
        <span class="poblacion__icono">${ICONOS_POBLACION[clave]}</span>
        <div class="poblacion__cuerpo">
          <span class="poblacion__valor">${formatoNumero(valor)}</span>
          <span class="poblacion__etiqueta">${etiqueta}</span>
          <div class="poblacion__barra" title="${pct}% de las personas afectadas"><span style="width:${pct}%"></span></div>
        </div>
      </div>`;
    }).join('');
  }

  async function cargarTablero() {
    const id = ++peticionActual;
    actualizarResumenDeFiltros();
    $('bloqueIndicadores').classList.add('cargando');
    const params = construirParametros().toString();
    try {
      const resp = await fetch(`/api/casos/resumen/${params ? '?' + params : ''}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const resumen = await resp.json();
      if (id !== peticionActual) return; // llegó una respuesta más nueva

      ultimoResumen = resumen;
      $('errorTablero').classList.add('d-none');
      $('totalObservatorios').textContent = formatoNumero(resumen.total_observatorios);
      $('notaObservatorios').textContent = bloquearTerritorio ? 'En tu observatorio'
        : hayFiltroTerritorial() ? 'Dentro del territorio elegido' : 'En toda la Red';
      $('totalCasos').textContent = formatoNumero(resumen.total_casos);
      $('totalPersonas').textContent = formatoNumero(resumen.poblacion.personas);
      $('notaCasos').textContent = notaDelPeriodo();
      $('notaPersonas').textContent = notaDelPeriodo();
      $('totalMunicipios').textContent = formatoNumero(resumen.municipios_con_reportes);
      const deps = resumen.departamentos_con_reportes || 0;
      $('notaMunicipios').textContent = `En ${formatoNumero(deps)} ${deps === 1 ? 'departamento' : 'departamentos'}`;
      $('ultimaActualizacion').textContent = formatoFecha(resumen.ultima_actualizacion);
      dibujarBarras();
      dibujarTipoHecho(resumen.por_tipo_hecho);
      dibujarMeses(resumen.por_mes);
      dibujarPoblacion(resumen.poblacion);
    } catch (e) {
      if (id === peticionActual) $('errorTablero').classList.remove('d-none');
    } finally {
      if (id === peticionActual) $('bloqueIndicadores').classList.remove('cargando');
    }
    if (typeof cfg.alActualizar === 'function') cfg.alActualizar(params);
  }

  // ---------------------------------------------------------------
  // Eventos
  // ---------------------------------------------------------------
  $('fPeriodo').addEventListener('change', () => { actualizarCamposDeFecha(); cargarTablero(); });
  $('fDesde').addEventListener('change', cargarTablero);
  $('fHasta').addEventListener('change', cargarTablero);

  $('fDepartamento').addEventListener('change', () => {
    $('fMunicipio').value = '';
    $('fObservatorio').value = '';
    llenarMunicipios();
    llenarObservatorios();
    cargarTablero();
  });
  $('fMunicipio').addEventListener('change', () => {
    $('fObservatorio').value = '';
    llenarObservatorios();
    cargarTablero();
  });
  $('fObservatorio').addEventListener('change', cargarTablero);
  $('fTipoHecho').addEventListener('change', cargarTablero);
  document.querySelectorAll('input[name="vistaBarras"]').forEach(r => r.addEventListener('change', dibujarBarras));
  $('fTopBarras').addEventListener('change', dibujarBarras);

  $('btnLimpiar').addEventListener('click', () => {
    $('fPeriodo').value = periodoInicial;
    $('fDesde').value = '';
    $('fHasta').value = '';
    $('fTipoHecho').value = '';
    if (!bloquearTerritorio) {
      $('fDepartamento').value = '';
      $('fMunicipio').value = '';
      $('fObservatorio').value = '';
      llenarMunicipios();
      llenarObservatorios();
    }
    actualizarCamposDeFecha();
    cargarTablero();
  });

  (async function iniciar() {
    $('fPeriodo').value = periodoInicial;
    actualizarCamposDeFecha();
    try {
      await cargarOpcionesDeFiltros();
    } catch (e) {
      // Si fallan los desplegables, el tablero igual muestra las cifras sin filtrar.
    }
    cargarTablero();
  })();
})();
