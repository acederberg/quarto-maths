
const uvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;

/*
// Example log entry
const logEntry = '172.19.0.1:59142 - "GET /site_libs/quarto-html/53fff1658bb29a86a77f917560521602.css.map HTTP/1.1" 404';

// Match the log entry
const match = logEntry.match(logPattern);

if (match) {
  console.log(match.groups); // Parsed log parts
}
*/




async function hydrateLiveLogLine(container, item) {

  const elem = document.createElement("tr")
  const itemTime = document.createElement("td")
  const itemName = document.createElement("td")
  const itemMsg = document.createElement("td")
  const itemLevel = document.createElement("td")

  itemTime.textContent = '[' + item.created_time + ']'
  itemLevel.textContent = item.levelname
  itemName.textContent = item.name + ":" + item.lineno

  const matched = item.msg.match(uvicornLogPattern)
  console.log(matched)

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

  // console.log(container)
  // const tabItem = container.closest(".tab-item")
  // if (!tabItem) throw Error("Could not find tab item for table.")
  //
  // tabItem.scollTop = tabItem.scrollHeight

}

async function hydrateLiveLog() {

  const parent = document.querySelector("#tab-content-1")
  const container = document.querySelector("#live-logs-server tbody")
  if (!container) throw Error("Could not find `live-logs-server`.")
  console.log("container", container)
  const ws = new WebSocket("/api/dev/log")

  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened."),
  )
  ws.addEventListener(
    "message",
    (event) => {
      const data = JSON.parse(event.data)
      data.items.map(item => hydrateLiveLogLine(container, item))

      parent.scrollTop = parent.scrollHeight
      console.log(parent.scrollHeight)
    },
  )


}
