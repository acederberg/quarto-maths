
const PDF_VIEW_VERBOSE = true

function QuartoPDFViewer(quarto, { iframeLeft, iframeRight }) {
  const ws = quarto.ws

  function reload() {
    iframeLeft.src = iframeLeft.src
    iframeRight.src = iframeRight.src
  }

  ws.addEventListener("message", (event) => {
    const data = JSON.parse(event.data)
    data.items.map(item => {
      if (item.target == "blog/resume/resume.qmd") reload()
    })
  })

  return { quarto, reload }
}

function PDFViewer(quartoDev) {
  const pdfDevPage = QuartoPDFViewer(quartoDev, {
    iframeLeft: document.getElementById("live-tex"),
    iframeRight: document.getElementById("live-pdf"),
  })
  globalThis.pdfDevPage = pdfDevPage
}


function QuartoHTMLViewer(quarto, { iframe }) {
  const ws = quarto.ws
  const iframeParent = iframe.closest("div")

  function reload() {
    iframe.source = iframe.source
    iframeParent.classList.add("new")
    setTimeout(() => iframeParent.classList.remove("new"), 1000)
  }

  ws.addEventListener("message", (event) => {
    const data = JSON.parse(event.data)
    data.items.map(item => {
      if (item.target == "blog/dev/live.qmd") reload()
    })
  })

  return { quarto, reload }

}

