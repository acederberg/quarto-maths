
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
      PDF_VIEW_VERBOSE && console.log(item)
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

  const pdf = document.getElementById("pdf")
  // pdf.style.filter = "brightness(0.5)"
}

