// .activities-controls__col { flex: 0; -webkit-flex: 0; flex-shrink: 0; -webkit-flex-shrink: 0; }
// .ui-rowfeed-rowbase { display: block !important; }

const style = document.createElement('style');
style.innerHTML = `
 .activities-controls__col { flex: 0.25 !important; -webkit-flex: 0.25 !important; flex-shrink: 0 !important; -webkit-flex-shrink: 0 !important; }
 .ui-rowfeed-rowbase { display: block !important; }
 .activities-controls__col--align-right { display: block !important}
`

document.head.appendChild(style);