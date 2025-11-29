// rpt-all-py.js (Updated generateWhatsAppText function and date selection)
require('dotenv').config();
//¿cambio?

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const readlineSync = require('readline-sync');

const NOZBE_API_URL = 'https://api4.nozbe.com/v1/api';
const NOZBE_API_KEY = process.env.NOZBE_API_KEY;

// --- Definir la carpeta de reportes ---
const REPORTS_DIR = 'reports';

if (!NOZBE_API_KEY) {
    console.error('Error: La variable de entorno NOZBE_API_KEY no está definida.');
    process.exit(1);
}

// --- Función para formatear timestamps (milisegundos) a YY-MM-DD ---
const formatTimestampToYYMMDD = (timestamp) => {
    if (!timestamp) {
        return 'N/A';
    }
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
        return 'Fecha inválida';
    }
    const year = date.getFullYear().toString().slice(-2);
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
};

// --- Función para formatear milisegundos a formato Hh Mm ---
const formatMillisecondsToHM = (ms) => {
    if (typeof ms !== 'number' || ms < 0) {
        return '0h 0m';
    }
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    let result = '';
    if (hours > 0) {
        result += `${hours}h `;
    }
    result += `${minutes}m`;
    return result.trim();
};

// --- Función para generar PDF (CON MÁRGENES Y FUENTE MONOSPACE) ---
const generatePdf = async (htmlContent, filePath) => {
    let browser;
    try {
        browser = await puppeteer.launch({ headless: true });
        const page = await browser.newPage();
        await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

        await page.pdf({
            path: filePath,
            format: 'letter',
            printBackground: true,
            margin: {
                top: '1in',
                right: '1in',
                bottom: '1in',
                left: '1in'
            }
        });
        console.log(`PDF generado: ${filePath}`);
    } catch (error) {
        console.error(`Error al generar el PDF ${filePath}:`, error.message);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
};

// --- Función para generar texto amigable para WhatsApp (SIN GUIONES EN TÍTULOS y con tiempos) ---
const generateWhatsAppText = (htmlContent, filePath) => {
    let textContent = htmlContent;

    // AÑADIR ESTE PASO INICIAL: Eliminar completamente las etiquetas <style> y su contenido
    textContent = textContent.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '');

    // Paso 1: Reemplazar entidades HTML
    textContent = textContent.replace(/&amp;/g, '&');
    textContent = textContent.replace(/&lt;/g, '<');
    textContent = textContent.replace(/&gt;/g, '>');
    textContent = textContent.replace(/&quot;/g, '"');
    textContent = textContent.replace(/&#39;/g, "'");

    // Paso 2: Convertir encabezados HTML a negritas para WhatsApp (AHORA SIN GUIONES)
    textContent = textContent.replace(/<h1>(.*?)<\/h1>/g, '\n\n*$1*\n');
    textContent = textContent.replace(/<h2>(.*?)<\/h2>/g, '\n\n*$1*\n');
    textContent = textContent.replace(/<h3>(.*?)<\/h3>/g, '\n\n*$1*\n');
    textContent = textContent.replace(/<h4>(.*?)<\/h4>/g, '\n\n*$1*\n');

    // Paso 3: Convertir elementos de lista de tareas con sus detalles y tiempos
    // Tareas completadas con Venc., Fin., Real., Est.
    textContent = textContent.replace(/<li class="task-item">☑ Completada: (.*?) \(Venc\.: (.*?)\) \(Fin\.: (.*?)\) \(Real\.: (.*?)\) \(Est\.: (.*?)\)<\/li>/g, '☑ Completa: $1 (Real.: $4 / Est.: $5)\n');
    // Tareas pendientes con Venc., Fin.(N/A), Real., Est.
    textContent = textContent.replace(/<li class="task-item">☐ Pendiente: (.*?) \(Venc\.: (.*?)\) \(Fin\.: N\/A\) \(Real\.: (.*?)\) \(Est\.: (.*?)\)<\/li>/g, '☐ Pendiente: $1 (Venc.: $2) (Real.: $3 / Est.: $4)\n');
    
    // Paso 4: Convertir etiquetas de negrita (<strong>) a *negrita* para WhatsApp
    textContent = textContent.replace(/<strong>(.*?)<\/strong>/g, '*$1*');

    // Paso 5: Reemplazar la línea horizontal con un separador de texto
    textContent = textContent.replace(/<hr\b[^>]*>/g, '\n-------------------------------\n');
    
    // Convertir párrafos a texto plano con salto de línea
    textContent = textContent.replace(/<p\b[^>]*>(.*?)<\/p>/g, '$1\n');
    
    // Extraer y formatear los totales de sección/proyecto (usando las nuevas clases)
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Totales Proyecto:<\/strong> Real\. (.*?) \/ Est\. (.*?)<\/div>/g, '\n*Totales Proyecto:* Real. $1 / Est. $2\n');
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Total Tareas Completadas:<\/strong> (.*?)<\/div>/g, '\n*Total Tareas Completadas:* $1\n');
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Total Tareas Relevantes:<\/strong> (.*?)<\/div>/g, '\n*Total Tareas Relevantes:* $1\n');
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Porcentaje de Completado:<\/strong> (.*?)<\/div>/g, '\n*Porcentaje de Completado:* $1\n');
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Tiempo Realizado:<\/strong> (.*?)<\/div>/g, '\n*Tiempo Realizado:* $1\n');
    textContent = textContent.replace(/<div class="project-summary-item">\s*<strong>Tiempo Estimado:<\/strong> (.*?)<\/div>/g, '\n*Tiempo Estimado:* $1\n');

    // Manejar el resumen global
    textContent = textContent.replace(/<div class="global-summary">.*?<h1>(.*?)<\/h1>\s*<p class="summary-line">(.*?)<\/p>\s*<p class="summary-line">(.*?)<\/p>\s*<p class="summary-line">(.*?)<\/p>\s*<p class="summary-line">(.*?)<\/p>\s*<p class="summary-line">(.*?)<\/p>\s*<p class="summary-line">(.*?)<\/p>\s*<\/div>/gs, (match, title, ...lines) => {
        let formattedLines = lines.map(line => line.replace(/<strong>(.*?)<\/strong>/g, '*$1*').trim());
        return `\n\n*${title}*\n\n${formattedLines.join('\n')}\n`;
    });


    // Eliminar el resto de etiquetas HTML que no son necesarias (ul, /ul, etc.)
    // Esta expresión regular debe ir al final para limpiar todo lo que no haya sido transformado
    textContent = textContent.replace(/<[^>]*>/g, '');

    // Paso 6: Limpiar saltos de línea excesivos y espacios en blanco al principio/final
    textContent = textContent.replace(/\n\n\n+/g, '\n\n');
    textContent = textContent.replace(/^\s*\n/gm, '');
    textContent = textContent.replace(/\s+$/gm, '');

    fs.writeFileSync(filePath, textContent.trim());
    console.log(`Texto para WhatsApp generado: ${filePath}`);
};


const getNozbeData = async (endpoint, params = {}) => {
    try {
        const response = await axios.get(`${NOZBE_API_URL}/${endpoint}`, {
            headers: {
                'Authorization': `apikey ${NOZBE_API_KEY}`,
                'Accept': 'application/json'
            },
            params: params
        });
        return response.data;
    } catch (error) {
        console.error(`Error al obtener datos de ${endpoint}:`, error.message);
        if (error.response) {
            console.error('Datos de error de la API:', error.response.data);
        }
        throw error;
    }
};

const generateReport = async () => {
    try {
        // --- Crear la carpeta de reportes si no existe ---
        if (!fs.existsSync(REPORTS_DIR)) {
            fs.mkdirSync(REPORTS_DIR);
            console.log(`Carpeta '${REPORTS_DIR}' creada.`);
        }

        console.log('Obteniendo equipos disponibles...');
        const allTeams = await getNozbeData('teams');
        if (allTeams.length === 0) {
            console.log('No se encontraron equipos. Asegúrate de que tu API Key sea válida y tengas equipos asociados.');
            return;
        }

        console.log('Equipos disponibles:');
        allTeams.forEach((team, index) => {
            console.log(`${index + 1}. ${team.name} (ID: ${team.id})`);
        });

        const selectedTeamsInput = readlineSync.question('Ingresa los números de los equipos para los que deseas generar el reporte (separados por comas, ej: 1,3,5): ');
        const selectedTeamIndices = selectedTeamsInput.split(',').map(s => parseInt(s.trim(), 10) - 1).filter(index => !isNaN(index) && index >= 0 && index < allTeams.length);

        if (selectedTeamIndices.length === 0) {
            console.log('No se seleccionaron equipos válidos. Saliendo del programa.');
            return;
        }

        const targetTeamIds = selectedTeamIndices.map(index => allTeams[index].id);
        const targetTeamNames = selectedTeamIndices.map(index => allTeams[index].name);

        console.log(`Generando reportes para los equipos: ${targetTeamNames.join(', ')}`);

        // --- Preguntar al usuario si quiere la semana actual o la semana anterior ---
        const weekSelection = readlineSync.question('¿Quieres el reporte para la *semana actual* (1) o la *semana anterior* (2)? (1/2): ');
        const usePreviousWeek = weekSelection === '2';

        // Totales generales para todo el equipo seleccionado
        let grandTotalTeamCompleted = 0;
        let grandTotalTeamTasks = 0;
        let grandTotalTeamTimeSpent = 0;
        let grandTotalTeamTimeNeeded = 0;

        // Iterar sobre cada equipo seleccionado y generar su reporte
        for (const currentTeamId of targetTeamIds) {
            const currentTeamName = allTeams.find(team => team.id === currentTeamId).name;
            console.log(`\n--- Procesando equipo: ${currentTeamName} (ID: ${currentTeamId}) ---`);

            console.log('Obteniendo proyectos...');
            const allProjects = await getNozbeData('projects', { limit: 1000 });

            const teamProjects = allProjects.filter(project =>
                project.team_id === currentTeamId &&
                project.ended_at === null
            );
            const teamProjectIds = teamProjects.map(project => project.id);

            console.log(`Proyectos ACTIVOS encontrados para el equipo ${currentTeamName}: ${teamProjects.length}`);

            console.log('Obteniendo tareas...');
            const allTasks = await getNozbeData('tasks', {
                limit: 2000,
                offset: 0,
                sortBy: '-ended_at'
            });

            const teamTasks = allTasks.filter(task => teamProjectIds.includes(task.project_id));
            console.log(`Tareas encontradas en proyectos activos para el equipo (antes de filtro de relevancia): ${teamTasks.length}`);

            // --- Lógica de cálculo del rango semanal (Lunes a Domingo) para la semana seleccionada ---
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            let mondayReference = new Date(today);
            if (usePreviousWeek) {
                // Si es la semana anterior, retrocedemos 7 días
                mondayReference.setDate(today.getDate() - (today.getDay() === 0 ? 6 : today.getDay() - 1) - 7);
            } else {
                // Si es la semana actual, calculamos el lunes de esta semana
                mondayReference.setDate(today.getDate() - (today.getDay() === 0 ? 6 : today.getDay() - 1));
            }
            mondayReference.setHours(0, 0, 0, 0);
            const mondayThisWeek = mondayReference;
            const mondayThisWeekTimestampMs = mondayThisWeek.getTime();

            const sundayThisWeek = new Date(mondayThisWeek);
            sundayThisWeek.setDate(mondayThisWeek.getDate() + 6);
            sundayThisWeek.setHours(23, 59, 59, 999);
            const sundayThisWeekTimestampMs = sundayThisWeek.getTime();

            const mondayNextWeek = new Date(sundayThisWeek);
            mondayNextWeek.setDate(sundayThisWeek.getDate() + 1); 
            mondayNextWeek.setHours(0, 0, 0, 0);
            const mondayNextWeekTimestampMs = mondayNextWeek.getTime();

            const sundayNextWeek = new Date(mondayNextWeek);
            sundayNextWeek.setDate(mondayNextWeek.getDate() + 6);
            sundayNextWeek.setHours(23, 59, 59, 999);
            const sundayNextWeekTimestampMs = sundayNextWeek.getTime();

            console.log(`Reporte para la semana seleccionada: ${formatTimestampToYYMMDD(mondayThisWeek.getTime())} - ${formatTimestampToYYMMDD(sundayThisWeek.getTime())}`);
            console.log(`Tareas pendientes consideradas hasta la siguiente semana: ${formatTimestampToYYMMDD(mondayNextWeek.getTime())} - ${formatTimestampToYYMMDD(sundayNextWeek.getTime())}`);


            // --- Filtro Principal: Tareas completadas en la semana seleccionada O activas con due_at en la semana seleccionada/próxima ---
            const relevantTasks = teamTasks.filter(task => {
                // Tareas completadas en la semana seleccionada
                if (task.ended_at !== null && typeof task.ended_at === 'number' && task.ended_at > 0) {
                    const endedAtTimestampMs = task.ended_at;
                    return endedAtTimestampMs >= mondayThisWeekTimestampMs && endedAtTimestampMs <= sundayThisWeekTimestampMs;
                }
                // Tareas pendientes con vencimiento en la semana seleccionada o la próxima
                if (task.ended_at === null && typeof task.due_at === 'number' && task.due_at > 0) {
                    const dueAtTimestampMs = task.due_at;
                    const dueThisWeekSelected = dueAtTimestampMs >= mondayThisWeekTimestampMs && dueAtTimestampMs <= sundayThisWeekTimestampMs;
                    const dueNextWeek = dueAtTimestampMs >= mondayNextWeekTimestampMs && dueAtTimestampMs <= sundayNextWeekTimestampMs;
                    return dueThisWeekSelected || dueNextWeek;
                }
                return false;
            });
            console.log(`Tareas relevantes (filtradas por nueva lógica): ${relevantTasks.length}`);


            // --- Lógica para agrupar las tareas relevantes por proyecto y calcular totales ---
            const tasksByProjectId = {};
            relevantTasks.forEach(task => {
                if (task.project_id) {
                    if (!tasksByProjectId[task.project_id]) {
                        tasksByProjectId[task.project_id] = { 
                            completed: [], 
                            pending: [],
                            totalTimeSpent: 0,
                            totalTimeNeeded: 0
                        };
                    }
                    if (task.ended_at !== null) {
                        tasksByProjectId[task.project_id].completed.push(task);
                    } else {
                        tasksByProjectId[task.project_id].pending.push(task);
                    }
                    // Sumar tiempos a los totales del proyecto
                    tasksByProjectId[task.project_id].totalTimeSpent += (task.time_spent || 0);
                    tasksByProjectId[task.project_id].totalTimeNeeded += (task.time_needed || 0);
                }
            });

            // --- Lógica de conteo de tareas completadas y totales por proyecto ---
            const completedTasksByProject = {};
            const totalTasksByProject = {};
            let teamTimeSpentThisReport = 0;
            let teamTimeNeededThisReport = 0;


            relevantTasks.forEach(task => {
                if (task.project_id) {
                    if (!totalTasksByProject[task.project_id]) {
                        totalTasksByProject[task.project_id] = 0;
                        completedTasksByProject[task.project_id] = 0;
                    }
                    totalTasksByProject[task.project_id]++;

                    if (task.ended_at !== null) {
                        completedTasksByProject[task.project_id]++;
                    }
                }
                // Sumar al total del equipo para este reporte (sólo tareas relevantes)
                teamTimeSpentThisReport += (task.time_spent || 0);
                teamTimeNeededThisReport += (task.time_needed || 0);
            });

            const totalTeamCompleted = Object.values(completedTasksByProject).reduce((sum, count) => sum + count, 0);
            const totalTeamTasks = Object.values(totalTasksByProject).reduce((sum, count) => sum + count, 0);
            const teamCompletionPercentage = totalTeamTasks > 0 ? ((totalTeamCompleted / totalTeamTasks) * 100).toFixed(2) : 0;

            // Acumular a los totales GRANDES del equipo seleccionado
            grandTotalTeamCompleted += totalTeamCompleted;
            grandTotalTeamTasks += totalTeamTasks;
            grandTotalTeamTimeSpent += teamTimeSpentThisReport;
            grandTotalTeamTimeNeeded += teamTimeNeededThisReport;


            console.log('\n--- Generando Reporte HTML ---');
            let htmlReport = `
<style>
  body {
    font-family: monospace; /* Fuente monospace para todo el cuerpo */
    font-size: 10pt; /* Tamaño de fuente ajustable */
    line-height: 1.4;
  }
  /* Asegurar que los encabezados también usen monospace */
  h1, h2, h3, h4, li, p, ul {
    font-family: monospace;
  }
  .project-name-header {
    margin-bottom: 5px;
  }
  .task-list {
    margin-bottom: 15px;
  }
  .task-item {
    margin-bottom: 3px;
  }
  .project-summary-item {
    font-size: 9.5pt;
    margin-top: 5px;
    margin-bottom: 5px;
  }
  hr {
    border: 0;
    border-top: 1px dashed #ccc;
    margin: 20px 0;
  }
</style>
<h1>Reporte de tareas del equipo: ${currentTeamName}</h1>
<h2>Periodo de Relevancia: ${formatTimestampToYYMMDD(mondayThisWeek.getTime())} - ${formatTimestampToYYMMDD(sundayNextWeek.getTime())}</h2>
<h3>Proyectos y sus Tareas:</h3>`;

            teamProjects.forEach(project => {
                const projectId = project.id;
                const projectName = project.name;
                const completed = completedTasksByProject[projectId] || 0;
                const total = totalTasksByProject[projectId] || 0;
                const percentage = total > 0 ? ((completed / total) * 100).toFixed(2) : 0;

                const projectTimes = tasksByProjectId[projectId] || { totalTimeSpent: 0, totalTimeNeeded: 0 };
                const projectTimeSpentFormatted = formatMillisecondsToHM(projectTimes.totalTimeSpent);
                const projectTimeNeededFormatted = formatMillisecondsToHM(projectTimes.totalTimeNeeded);


                if (tasksByProjectId[projectId] && (tasksByProjectId[projectId].completed.length > 0 || tasksByProjectId[projectId].pending.length > 0)) {
                    htmlReport += `<h4 class="project-name-header">Proyecto: ${projectName} (${completed}/${total} tareas - ${percentage}%)</h4>
<div class="project-summary-item"><strong>Totales Proyecto:</strong> Real. ${projectTimeSpentFormatted} / Est. ${projectTimeNeededFormatted}</div>
<ul class="task-list">`;

                    // Ordenar tareas completadas por fecha de finalización
                    tasksByProjectId[projectId].completed.sort((a, b) => a.ended_at - b.ended_at);
                    
                    tasksByProjectId[projectId].completed.forEach(task => {
                        let taskName = task.name;
                        const endedDate = task.ended_at ? formatTimestampToYYMMDD(task.ended_at) : 'N/A';
                        const taskTimeSpentFormatted = formatMillisecondsToHM(task.time_spent);
                        const taskTimeNeededFormatted = formatMillisecondsToHM(task.time_needed);

                        htmlReport += `<li class="task-item">☑ Completada: ${taskName} (Venc.: ${formatTimestampToYYMMDD(task.due_at)}) (Fin.: ${endedDate}) (Real.: ${taskTimeSpentFormatted}) (Est.: ${taskTimeNeededFormatted})</li>`;
                    });

                    // Ordenar tareas pendientes por fecha de vencimiento
                    tasksByProjectId[projectId].pending.sort((a, b) => {
                        const dueA = (typeof a.due_at === 'number' && a.due_at > 0) ? a.due_at : Infinity;
                        const dueB = (typeof b.due_at === 'number' && b.due_at > 0) ? b.due_at : Infinity;
                        return dueA - dueB;
                    });

                    tasksByProjectId[projectId].pending.forEach(task => {
                        let taskName = task.name;
                        let dueDateString = (typeof task.due_at === 'number' && task.due_at > 0) ? formatTimestampToYYMMDD(task.due_at) : 'N/A';
                        const taskTimeSpentFormatted = formatMillisecondsToHM(task.time_spent);
                        const taskTimeNeededFormatted = formatMillisecondsToHM(task.time_needed);
                        
                        // Añadir "Fin.: N/A" para las tareas pendientes por coherencia en el formato
                        htmlReport += `<li class="task-item">☐ Pendiente: ${taskName} (Venc.: ${dueDateString}) (Fin.: N/A) (Real.: ${taskTimeSpentFormatted}) (Est.: ${taskTimeNeededFormatted})</li>`;
                    });

                    htmlReport += `</ul>`;
                }
            });

            htmlReport += `<hr><h2>Resumen de Tareas Relevantes del Equipo ${currentTeamName}:</h2>
                            <div class="project-summary-item"><strong>Total Tareas Completadas:</strong> ${totalTeamCompleted}</div>
                            <div class="project-summary-item"><strong>Total Tareas Relevantes:</strong> ${totalTeamTasks}</div>
                            <div class="project-summary-item"><strong>Porcentaje de Completado:</strong> ${teamCompletionPercentage}%</div>
                            <div class="project-summary-item"><strong>Tiempo Realizado:</strong> ${formatMillisecondsToHM(teamTimeSpentThisReport)}</div>
                            <div class="project-summary-item"><strong>Tiempo Estimado:</strong> ${formatMillisecondsToHM(teamTimeNeededThisReport)}</div>`;

            // --- Generar todos los formatos de reporte ---
            const todaydate = formatTimestampToYYMMDD(new Date().getTime());
            const reportFileNameBase = `reporte-tareas-${currentTeamName.replace(/\s+/g, '-')}-${todaydate}${usePreviousWeek ? '-semana-anterior' : ''}`; // Nombre de archivo más específico
            // --- Usar path.join para construir rutas de archivo ---
            const htmlFilePath = path.join(REPORTS_DIR, `${reportFileNameBase}.html`);
            const pdfFilePath = path.join(REPORTS_DIR, `${reportFileNameBase}.pdf`);
            const whatsappFilePath = path.join(REPORTS_DIR, `${reportFileNameBase}_whatsapp.txt`);

            fs.writeFileSync(htmlFilePath, htmlReport);
            console.log(`\nReporte HTML generado: ${htmlFilePath}`);

            await generatePdf(htmlReport, pdfFilePath);

            generateWhatsAppText(htmlReport, whatsappFilePath);
        } // Fin del bucle for (currentTeamId of targetTeamIds)

        // Si se seleccionó más de un equipo, generar un resumen global
        if (targetTeamIds.length > 1) {
            console.log('\n--- Generando Resumen Global de Equipos ---');
            const globalSummaryHtml = `
<style>
  body {
    font-family: monospace;
    font-size: 10pt;
    line-height: 1.4;
  }
  h1, h2, h3, h4, li, p, ul {
    font-family: monospace;
  }
  .global-summary {
    margin-top: 30px;
    padding: 15px;
    border: 2px solid #000;
    background-color: #f9f9f9;
    page-break-before: always;
  }
  .summary-line {
    font-weight: bold;
    margin-bottom: 5px;
  }
</style>
<div class="global-summary">
  <h1>Resumen Global de Tareas de Equipos Seleccionados</h1>
  <p class="summary-line"><strong>Total Equipos Reportados:</strong> ${targetTeamNames.join(', ')}</p>
  <p class="summary-line"><strong>Total Tareas Completadas (Relevantes):</strong> ${grandTotalTeamCompleted}</p>
  <p class="summary-line"><strong>Total Tareas Relevantes:</strong> ${grandTotalTeamTasks}</p>
  <p class="summary-line"><strong>Porcentaje de Completado Global:</strong> ${grandTotalTeamTasks > 0 ? ((grandTotalTeamCompleted / grandTotalTeamTasks) * 100).toFixed(2) : 0}%</p>
  <p class="summary-line"><strong>Tiempo Realizado Global:</strong> ${formatMillisecondsToHM(grandTotalTeamTimeSpent)}</p>
  <p class="summary-line"><strong>Tiempo Estimado Global:</strong> ${formatMillisecondsToHM(grandTotalTeamTimeNeeded)}</p>
</div>`;

            const todaydate = formatTimestampToYYMMDD(new Date().getTime());
            const globalReportFileNameBase = `resumen-global-tareas-${todaydate}${usePreviousWeek ? '-semana-anterior' : ''}`;
            const globalHtmlFilePath = path.join(REPORTS_DIR, `${globalReportFileNameBase}.html`);
            const globalPdfFilePath = path.join(REPORTS_DIR, `${globalReportFileNameBase}.pdf`);
            const globalWhatsappFilePath = path.join(REPORTS_DIR, `${globalReportFileNameBase}_whatsapp.txt`);

            fs.writeFileSync(globalHtmlFilePath, globalSummaryHtml);
            console.log(`\nResumen Global HTML generado: ${globalHtmlFilePath}`);
            await generatePdf(globalSummaryHtml, globalPdfFilePath);

            // Adapta la generación de WhatsApp para el resumen global
            let globalWhatsappContent = `*Resumen Global de Tareas de Equipos Seleccionados*\n\n`;
            globalWhatsappContent += `*Total Equipos Reportados:* ${targetTeamNames.join(', ')}\n`;
            globalWhatsappContent += `*Total Tareas Completadas (Relevantes):* ${grandTotalTeamCompleted}\n`;
            globalWhatsappContent += `*Total Tareas Relevantes:* ${grandTotalTeamTasks}\n`;
            globalWhatsappContent += `*Porcentaje de Completado Global:* ${grandTotalTeamTasks > 0 ? ((grandTotalTeamCompleted / grandTotalTeamTasks) * 100).toFixed(2) : 0}%\n`;
            globalWhatsappContent += `*Tiempo Realizado Global:* ${formatMillisecondsToHM(grandTotalTeamTimeSpent)}\n`;
            globalWhatsappContent += `*Tiempo Estimado Global:* ${formatMillisecondsToHM(grandTotalTeamTimeNeeded)}\n`;
            fs.writeFileSync(globalWhatsappFilePath, globalWhatsappContent.trim());
            console.log(`Resumen Global para WhatsApp generado: ${globalWhatsappFilePath}`);
        }

    } catch (error) {
        console.error('Fallo al generar el reporte de tareas relevantes del equipo:', error);
    }
};

generateReport();