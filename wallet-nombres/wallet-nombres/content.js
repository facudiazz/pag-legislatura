let auth = ""
let movements = []
let next_data = {}
let finalMovs = []

const API_URL = "https://apisrv.itconsultoramutual.com.ar/api/CobrosPagos/GetComprobante"

const style = document.createElement("style")

const styles = `

  #tabletMov {
    position: relative;
  }

  .superViewer {
    position: absolute;
    inset: 0;
    background: white;
  }

  .showViewer {
    display: none;
  }

  .superViewerContainer {
    margin-block: 1rem;
    border-bottom: 1px solid #000;
  }

  .superViewerFechaMonto {
    color: #1c6a94;
    display: flex;
    gap: 2rem;
    font-weight: 600;
  }

  .superViewerMonto {
    color: green;
  }

  .superViewerCoelsa {
    opacity: 0.8;
  }

  .toggleSuperViewer {
    background-color: #1c6a94;
    color: white;
    padding: 0.25rem 1.5rem;
    border-radius: 5px;
    margin-left: 1rem;
    transition: background-color 150ms ease
  }

  .toggleSuperViewer:hover {
    background-color: #1f6fcf
  }
`

style.innerText = styles

const superViewer = document.createElement("div")
superViewer.classList.add("superViewer")

const toggle = document.createElement('button')
toggle.setAttribute("type", "button")
toggle.classList.add("toggleSuperViewer")
toggle.textContent = "No Ver"
toggle.addEventListener("click", toggleViewer)

function toggleViewer() {
  document.querySelector(".superViewer").classList.toggle("showViewer")
  toggle.textContent = toggle.textContent == "No Ver" ? "Ver" : "No Ver"
}

function start() {
  next_data = JSON.parse(document.querySelector("script#__NEXT_DATA__").textContent)
  movements = next_data.props.pageProps.movimientos.filter(mov => mov.textoAgrupa == "Ingreso. TT").slice(0, 51)
  auth = "Bearer " + next_data.props.pageProps.session.user.Token

  document.head.appendChild(style)

  const promises = movements.map(mov => {
    return fetch(API_URL + "?id=" + mov.idTicket, {
        headers: { "Authorization": auth }
    })
    .then(res => res.json())
    .then(res => JSON.parse(res.jsonMsg));
});

  const formatter = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS"
  })

    Promise.allSettled(promises)
    .then(results => {
        finalMovs = results
            .filter(result => result.status === 'fulfilled')
            .map(result => result.value)
            .map(mov => {

              const split = mov.fechaHora.split("T")
              const fechaSplitted = split[0].split("-")
              const fecha = `${fechaSplitted[2]}/${fechaSplitted[1]}/${fechaSplitted[0]}`
              const hora = split[1].split(".")[0]
    
              return (
                `
              <div class="superViewerContainer">
                <div class="superViewerFechaMonto">
                  <span class="superViewerFecha">${fecha} - ${hora}</span>
                  <span class="superViewerMonto">${formatter.format(parseFloat(mov.monto).toFixed(2))}</span>
                </div>
                <div class="superViewerNombreCuit">
                  <span>${mov.nombreBeneficiario} - ${mov.cuitDestino}</span>
                </div>
                <div class="superViewerCoelsa">
                  <span>${mov.coelsaId}</span>
                </div>
              </div>
            `
              )
            });

        superViewer.innerHTML = "<h1>Ingresos a la Wallet</h1>" + finalMovs.join("")

        document.querySelector("#tabletMov").appendChild(superViewer)

        document.querySelector("#tabletMov").parentElement.firstChild.appendChild(toggle)
    });

}

start()