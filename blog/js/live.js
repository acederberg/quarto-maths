
const uvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;

async function hydrateLiveLogLine(container, item, index, array) {

  itemPrevious = index > 0 ? array[index - 1] : null
  console.log(itemPrevious)

  const elem = document.createElement("tr")
  const itemTime = document.createElement("td")
  const itemName = document.createElement("td")
  const itemMsg = document.createElement("td")
  const itemLevel = document.createElement("td")

  if (!itemPrevious || item.created_time != itemPrevious.created_time) {
    itemTime.textContent = '[' + item.created_time + ']'
  }
  itemLevel.textContent = item.levelname
  itemName.textContent = item.name + ":" + item.lineno

  const matched = item.msg.match(uvicornLogPattern)

  if (!matched) {
    itemMsg.textContent = item.msg
  }
  else {
    const { ip, port, method, path, protocol, status } = matched.groups

    const uvicornIp = document.createElement("span")
    const uvicornPort = document.createElement("span")
    const uvicornMethod = document.createElement("span")
    const uvicornPath = document.createElement("span")
    const uvicornStatus = document.createElement("span")
    const uvicornProtocol = document.createElement("span")

    uvicornIp.textContent = ip
    uvicornPort.textContent = " " + port
    uvicornMethod.textContent = " " + method
    uvicornPath.textContent = " " + path
    uvicornStatus.textContent = " " + status
    uvicornProtocol.textContent = " " + protocol

    uvicornIp.classList.add("uvicorn-ip")
    uvicornPort.classList.add("uvicorn-port")
    uvicornMethod.classList.add("uvicorn-method")
    uvicornPath.classList.add("uvicorn-path")
    uvicornStatus.classList.add("uvicorn-status")
    uvicornProtocol.classList.add("uvicorn-protocol")

    itemMsg.appendChild(uvicornIp)
    itemMsg.appendChild(uvicornPort)
    itemMsg.appendChild(uvicornMethod)
    itemMsg.appendChild(uvicornPath)
    itemMsg.appendChild(uvicornStatus)
    itemMsg.appendChild(uvicornProtocol)
  }



  itemTime.classList.add("terminal-row-time")
  itemLevel.classList.add("terminal-row-level")
  itemMsg.classList.add("terminal-row-msg")
  itemName.classList.add("terminal-row-name")

  itemLevel.classList.add(item.levelname.toLowerCase())

  elem.classList.add("terminal-row")
  elem.appendChild(itemTime)
  elem.appendChild(itemLevel)
  elem.appendChild(itemMsg)
  elem.appendChild(itemName)

  container.appendChild(elem)

}

async function hydrateLiveLog() {

  const parent = document.querySelector("#tab-content-1")
  const container = document.querySelector("#live-logs-server tbody")
  if (!container) throw Error("Could not find `live-logs-server`.")
  const ws = new WebSocket("/api/dev/log")

  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened for logs."),
  )
  ws.addEventListener(
    "message",
    (event) => {
      const data = JSON.parse(event.data)
      data.items.map((item, index, array) => hydrateLiveLogLine(container, item, index, array))

      parent.scrollTop = parent.scrollHeight
    },
  )


}




async function hydrateLiveLogQuarto(container, error) {
  if (!container) throw Error("Could not find `live-logs-quarto`.")

  const ws = new WebSocket(`/api/dev/quarto?error=${error}`)
  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened for quarto logs."),
  )
  ws.addEventListener("message", (event) => {
    const data = JSON.parse(event.data)
    if (!data.items.length) {
      const no_data = document.createElement("span")
      no_data.innerText = "No data."
      container.appendChild(no_data)
      return
    }
    const item = data.items[data.items.length - 1]

    container.innerHTML = ''

    const command = document.createElement("span")
    command.textContent = "Command: " + item.command
    command.classList.add("terminal-row", "quarto-command")

    const origin = document.createElement("span")
    origin.textContent = "Origin: " + item.origin
    origin.classList.add("terminal-row", "quarto-origin")

    const target = document.createElement("span")
    target.textContent = "Target: " + item.target
    target.classList.add("terminal-row", "quarto-target")

    const status = document.createElement("span")
    status.textContent = "Status: " + item.status_code
    status.classList.add("terminal-row", "quarto-exit-code")

    const spacer = document.createElement("span")
    spacer.classList.add("terminal-row")

    container.appendChild(command)
    container.appendChild(origin)
    container.appendChild(target)
    container.appendChild(status)
    container.appendChild(spacer)
    item.stdout.map(item => {
      const elem = document.createElement("span")
      elem.textContent = item
      elem.classList.add("terminal-row")
      container.appendChild(elem)
    })

  })
}
