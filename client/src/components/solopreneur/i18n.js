// ─────────────────────────────────────────────────────────────────────────────
// Solopreneur mode — compact UI dictionary.
//
// Mirrors the language switch in the approved mockup (EN / ES / FR). Only the
// interface chrome + section labels are translated; the underlying data
// (project names, task titles, updates…) is data, not UI copy, and stays as-is.
// ─────────────────────────────────────────────────────────────────────────────

export const LANG_LOCALE = { EN: 'en-GB', ES: 'es-ES', FR: 'fr-FR' }

export const I18N = {
  EN: {
    'nav.summary': 'Summary', 'nav.account': 'Account', 'nav.projects': 'Projects',
    'nav.wallet': 'Wallet', 'nav.updates': 'Updates', 'nav.messages': 'Messages',

    hello: 'Hello', todayIs: 'Today is', search: 'Search...', addProject: 'Add new project',
    logout: 'Log out', madeWith: 'Make with',

    'acc.title': 'Your account', 'acc.desc': 'The basics we keep about your business.',
    'acc.more': 'Add more details', 'acc.business': 'Business name', 'acc.owner': 'Owner',
    'acc.email': 'Email', 'acc.country': 'Country', 'acc.plan': 'Current plan',
    'acc.signin': 'Signed in with', 'acc.prefs': 'Preferences', 'acc.notify': 'Email notifications',

    'wal.title': 'Wallet',
    'wal.desc': 'Free credits from your sign-up. Used for AI work inside your projects.',
    'wal.plan': 'Plan', 'wal.billing': 'Billing', 'wal.invoice': 'Next invoice', 'wal.due': 'Due on',
    'wal.vat': 'Prices exclude VAT. Local VAT is added on your invoice.',
    'wal.add': 'Add credits', 'wal.change': 'Change plan', 'wal.credits': 'cxj credits',
    'wal.invoices': 'Invoices', 'wal.plans': 'Plans', 'wal.buy': 'Buy credits',
    'wal.choose': 'Choose', 'wal.current': 'Current plan',

    'gl.title': 'At a glance', 'gl.uptime': 'Uptime this month', 'gl.hours': 'Hours you got back',
    'gl.tasks': 'Tasks done for you', 'gl.projects': 'Active projects',

    'pr.title': 'Your projects', 'pr.desc': 'Everything we are building and running for you.',
    'pr.tasks': 'tasks', 'pr.done': 'done', 'pr.empty': 'No projects yet.',
    'pr.filter': 'Filter projects', 'pr.sortProgress': 'Sort: progress', 'pr.sortName': 'Sort: name',
    'pr.noTasks': 'No tasks on this project yet.',

    'tk.title': 'Tasks for today', 'tk.done': 'Done', 'tk.progress': 'In progress',
    'tk.empty': 'Nothing scheduled for today.', 'tk.markDone': 'Mark as done', 'tk.reopen': 'Reopen',

    'up.title': 'Latest updates',
    'up.desc': 'Everything your team did for you, in plain language.',
    'up.all': 'All updates', 'up.empty': 'No updates in this filter.',
    'up.markAllRead': 'Mark all as read', 'up.filterAll': 'All',
    'up.filterSystem': 'System', 'up.filterRelease': 'Releases',

    'wl.title': 'Latest activity',
    'wl.desc': 'Everything your team did for you, newest first.',
    'wl.open': 'Open activity', 'wl.empty': 'Nothing has happened yet.',
    'wl.error': 'The activity feed could not be loaded.', 'wl.retry': 'Try again',
    'wl.unread': 'unread',
    'wl.chat': 'Chat', 'wl.task': 'Task', 'wl.changes': 'Changes', 'wl.pr': 'Pull request',
    'wl.meet': 'Meet',

    'ms.title': 'Quick messages', 'ms.desc': 'Ask your hybrid team anything.',
    'ms.online': 'Your team is online', 'ms.ph': 'Ask your team anything...', 'ms.send': 'Send',
    'ms.you': 'You', 'ms.typing': 'Team is typing', 'ms.ai': 'CODEX-JUNIOR AI',

    'cal.title': 'Calendar', 'cal.askTeam': 'Message the team',

    'common.save': 'Save changes', 'common.cancel': 'Cancel', 'common.create': 'Create',
    'common.close': 'Close', 'common.required': 'This field is required.',
    'common.emailInvalid': 'Enter a valid email.',
    'common.fixErrors': 'Please review the highlighted fields.', 'common.on': 'On', 'common.off': 'Off',

    'np.title': 'Add new project', 'np.name': 'Project name', 'np.namePh': 'e.g. Spring campaign',
    'np.desc': 'We will set up the workspace and task list.', 'np.tasks': 'Initial tasks',

    'cp.title': 'Change plan', 'cp.desc': 'Switch any time. Prorated on your next invoice.',

    'lo.title': 'Log out?', 'lo.desc': 'You can sign back in at any time.',

    'toast.created': 'Project created', 'toast.credits': 'Credits added', 'toast.plan': 'Plan updated',
    'toast.saved': 'Changes saved', 'toast.taskDone': 'Task marked as done',
    'toast.taskReopened': 'Task reopened', 'toast.markedRead': 'All updates marked as read',
    'toast.lang': 'Language updated'
  },

  ES: {
    'nav.summary': 'Resumen', 'nav.account': 'Cuenta', 'nav.projects': 'Proyectos',
    'nav.wallet': 'Cartera', 'nav.updates': 'Novedades', 'nav.messages': 'Mensajes',

    hello: 'Hola', todayIs: 'Hoy es', search: 'Buscar...', addProject: 'Añadir proyecto',
    logout: 'Salir', madeWith: 'Hecho con',

    'acc.title': 'Tu cuenta', 'acc.desc': 'Lo básico que guardamos de tu negocio.',
    'acc.more': 'Añadir más datos', 'acc.business': 'Nombre del negocio', 'acc.owner': 'Propietario',
    'acc.email': 'Email', 'acc.country': 'País', 'acc.plan': 'Plan actual',
    'acc.signin': 'Sesión con', 'acc.prefs': 'Preferencias', 'acc.notify': 'Avisos por email',

    'wal.title': 'Cartera',
    'wal.desc': 'Créditos gratis de tu registro. Se usan para el trabajo de IA en tus proyectos.',
    'wal.plan': 'Plan', 'wal.billing': 'Facturación', 'wal.invoice': 'Próxima factura',
    'wal.due': 'Vence el', 'wal.vat': 'Precios sin IVA. El IVA local se añade en tu factura.',
    'wal.add': 'Añadir créditos', 'wal.change': 'Cambiar plan', 'wal.credits': 'créditos cxj',
    'wal.invoices': 'Facturas', 'wal.plans': 'Planes', 'wal.buy': 'Comprar créditos',
    'wal.choose': 'Elegir', 'wal.current': 'Plan actual',

    'gl.title': 'De un vistazo', 'gl.uptime': 'Disponibilidad este mes',
    'gl.hours': 'Horas que has ganado', 'gl.tasks': 'Tareas hechas por ti', 'gl.projects': 'Proyectos activos',

    'pr.title': 'Tus proyectos', 'pr.desc': 'Todo lo que construimos y mantenemos para ti.',
    'pr.tasks': 'tareas', 'pr.done': 'hecho', 'pr.empty': 'Aún no hay proyectos.',
    'pr.filter': 'Filtrar proyectos', 'pr.sortProgress': 'Orden: progreso', 'pr.sortName': 'Orden: nombre',
    'pr.noTasks': 'Todavía no hay tareas en este proyecto.',

    'tk.title': 'Tareas de hoy', 'tk.done': 'Hecho', 'tk.progress': 'En curso',
    'tk.empty': 'Nada programado para hoy.', 'tk.markDone': 'Marcar como hecho', 'tk.reopen': 'Reabrir',

    'up.title': 'Últimas novedades',
    'up.desc': 'Todo lo que tu equipo hizo por ti, en lenguaje claro.',
    'up.all': 'Todas las novedades', 'up.empty': 'No hay novedades con este filtro.',
    'up.markAllRead': 'Marcar todo leído', 'up.filterAll': 'Todo',
    'up.filterSystem': 'Sistema', 'up.filterRelease': 'Versiones',

    'wl.title': 'Actividad reciente',
    'wl.desc': 'Todo lo que tu equipo hizo por ti, lo más nuevo primero.',
    'wl.open': 'Abrir actividad', 'wl.empty': 'Todavía no ha pasado nada.',
    'wl.error': 'No se pudo cargar la actividad.', 'wl.retry': 'Reintentar',
    'wl.unread': 'sin leer',
    'wl.chat': 'Chat', 'wl.task': 'Tarea', 'wl.changes': 'Cambios', 'wl.pr': 'Pull request',
    'wl.meet': 'Reunión',

    'ms.title': 'Mensajes rápidos', 'ms.desc': 'Pregunta lo que quieras a tu equipo híbrido.',
    'ms.online': 'Tu equipo está en línea', 'ms.ph': 'Pregunta a tu equipo...', 'ms.send': 'Enviar',
    'ms.you': 'Tú', 'ms.typing': 'El equipo está escribiendo', 'ms.ai': 'CODEX-JUNIOR AI',

    'cal.title': 'Calendario', 'cal.askTeam': 'Escribir al equipo',

    'common.save': 'Guardar cambios', 'common.cancel': 'Cancelar', 'common.create': 'Crear',
    'common.close': 'Cerrar', 'common.required': 'Este campo es obligatorio.',
    'common.emailInvalid': 'Introduce un email válido.',
    'common.fixErrors': 'Revisa los campos marcados.', 'common.on': 'Sí', 'common.off': 'No',

    'np.title': 'Añadir proyecto', 'np.name': 'Nombre del proyecto',
    'np.namePh': 'p. ej. Campaña de primavera',
    'np.desc': 'Crearemos el espacio de trabajo y la lista de tareas.', 'np.tasks': 'Tareas iniciales',

    'cp.title': 'Cambiar plan', 'cp.desc': 'Cambia cuando quieras. Se prorratea en tu próxima factura.',

    'lo.title': '¿Salir?', 'lo.desc': 'Puedes volver a entrar cuando quieras.',

    'toast.created': 'Proyecto creado', 'toast.credits': 'Créditos añadidos',
    'toast.plan': 'Plan actualizado', 'toast.saved': 'Cambios guardados',
    'toast.taskDone': 'Tarea marcada como hecha', 'toast.taskReopened': 'Tarea reabierta',
    'toast.markedRead': 'Novedades marcadas como leídas', 'toast.lang': 'Idioma actualizado'
  },

  FR: {
    'nav.summary': 'Résumé', 'nav.account': 'Compte', 'nav.projects': 'Projets',
    'nav.wallet': 'Portefeuille', 'nav.updates': 'Nouveautés', 'nav.messages': 'Messages',

    hello: 'Bonjour', todayIs: 'Nous sommes le', search: 'Rechercher...', addProject: 'Ajouter un projet',
    logout: 'Déconnexion', madeWith: 'Fait avec',

    'acc.title': 'Votre compte', 'acc.desc': "Les informations de base de votre entreprise.",
    'acc.more': 'Ajouter des détails', 'acc.business': "Nom de l'entreprise", 'acc.owner': 'Propriétaire',
    'acc.email': 'E-mail', 'acc.country': 'Pays', 'acc.plan': 'Forfait actuel',
    'acc.signin': 'Connecté avec', 'acc.prefs': 'Préférences', 'acc.notify': 'Notifications e-mail',

    'wal.title': 'Portefeuille',
    'wal.desc': "Crédits offerts à l'inscription. Utilisés pour l'IA dans vos projets.",
    'wal.plan': 'Forfait', 'wal.billing': 'Facturation', 'wal.invoice': 'Prochaine facture',
    'wal.due': 'Échéance le', 'wal.vat': 'Prix hors taxes. La TVA locale est ajoutée sur votre facture.',
    'wal.add': 'Ajouter des crédits', 'wal.change': 'Changer de forfait', 'wal.credits': 'crédits cxj',
    'wal.invoices': 'Factures', 'wal.plans': 'Forfaits', 'wal.buy': 'Acheter des crédits',
    'wal.choose': 'Choisir', 'wal.current': 'Forfait actuel',

    'gl.title': "En un coup d'œil", 'gl.uptime': 'Disponibilité ce mois',
    'gl.hours': 'Heures gagnées', 'gl.tasks': 'Tâches réalisées pour vous', 'gl.projects': 'Projets actifs',

    'pr.title': 'Vos projets', 'pr.desc': 'Tout ce que nous construisons et maintenons pour vous.',
    'pr.tasks': 'tâches', 'pr.done': 'terminé', 'pr.empty': 'Aucun projet.',
    'pr.filter': 'Filtrer les projets', 'pr.sortProgress': 'Tri : avancement', 'pr.sortName': 'Tri : nom',
    'pr.noTasks': 'Aucune tâche pour ce projet.',

    'tk.title': 'Tâches du jour', 'tk.done': 'Terminé', 'tk.progress': 'En cours',
    'tk.empty': "Rien de prévu aujourd'hui.", 'tk.markDone': 'Marquer comme terminé', 'tk.reopen': 'Rouvrir',

    'up.title': 'Dernières nouveautés',
    'up.desc': 'Tout ce que votre équipe a fait, en clair.',
    'up.all': 'Toutes les nouveautés', 'up.empty': 'Aucune nouveauté pour ce filtre.',
    'up.markAllRead': 'Tout marquer comme lu', 'up.filterAll': 'Tout',
    'up.filterSystem': 'Système', 'up.filterRelease': 'Versions',

    'wl.title': 'Activité récente',
    'wl.desc': 'Tout ce que votre équipe a fait, du plus récent au plus ancien.',
    'wl.open': "Ouvrir l'activité", 'wl.empty': "Rien ne s'est encore passé.",
    'wl.error': "Impossible de charger l'activité.", 'wl.retry': 'Réessayer',
    'wl.unread': 'non lus',
    'wl.chat': 'Chat', 'wl.task': 'Tâche', 'wl.changes': 'Modifications', 'wl.pr': 'Pull request',
    'wl.meet': 'Réunion',

    'ms.title': 'Messages rapides', 'ms.desc': 'Demandez tout à votre équipe hybride.',
    'ms.online': 'Votre équipe est en ligne', 'ms.ph': 'Demandez à votre équipe...', 'ms.send': 'Envoyer',
    'ms.you': 'Vous', 'ms.typing': "L'équipe écrit", 'ms.ai': 'CODEX-JUNIOR AI',

    'cal.title': 'Calendrier', 'cal.askTeam': "Écrire à l'équipe",

    'common.save': 'Enregistrer', 'common.cancel': 'Annuler', 'common.create': 'Créer',
    'common.close': 'Fermer', 'common.required': 'Ce champ est obligatoire.',
    'common.emailInvalid': 'Saisissez un e-mail valide.',
    'common.fixErrors': 'Vérifiez les champs en rouge.', 'common.on': 'Oui', 'common.off': 'Non',

    'np.title': 'Ajouter un projet', 'np.name': 'Nom du projet',
    'np.namePh': 'ex. Campagne de printemps',
    'np.desc': "Nous créons l'espace de travail et la liste des tâches.", 'np.tasks': 'Tâches initiales',

    'cp.title': 'Changer de forfait',
    'cp.desc': 'Changez à tout moment. Proratisé sur la prochaine facture.',

    'lo.title': 'Se déconnecter ?', 'lo.desc': 'Vous pouvez vous reconnecter à tout moment.',

    'toast.created': 'Projet créé', 'toast.credits': 'Crédits ajoutés',
    'toast.plan': 'Forfait mis à jour', 'toast.saved': 'Modifications enregistrées',
    'toast.taskDone': 'Tâche terminée', 'toast.taskReopened': 'Tâche rouverte',
    'toast.markedRead': 'Nouveautés marquées comme lues', 'toast.lang': 'Langue mise à jour'
  }
}

export function translate(lang, key) {
  const dict = I18N[lang] || I18N.EN
  const value = dict[key]
  if (value !== undefined) return value
  return I18N.EN[key] !== undefined ? I18N.EN[key] : key
}