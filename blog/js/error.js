

const NO_ERROR_FOUND = "No Error Found."

async function hydrateError() {
  const error_response = await fetch("/error.json")

  const error_data = (error_response.status != 200) ? { command: NO_ERROR_FOUND, stdout: NO_ERROR_FOUND, stderr: NO_ERROR_FOUND, stderr: NO_ERROR_FOUND, } : await error_response.json()
  const error_stderr = document.querySelector("#error-stderr code")
  const error_stdout = document.querySelector("#error-stdout code")
  const error_command = document.querySelector("#error-command code")

  if (!error_stderr || !error_stdout || !error_command) {
    console.log(error_stderr, error_stdout, error_command)
    throw Error("Could not find all required elements.")
  }

  // error_stderr.textContent = error_data.stderr
  // error_command.textContent = error_data.command

  function addLines(values, parent) {
    if (!values.length) {
      const elem = document.createElement("span")
      elem.innerText = "No content."
      parent.appendChild(elem)
      return
    }

    values.map(item => {
      const elem = document.createElement("span")
      elem.textContent = item
      parent.appendChild(elem)
    })

  }

  addLines(error_data.stderr, error_stderr)
  addLines(error_data.command, error_command)
  addLines(error_data.stdout, error_stdout)

  const error_timestamp = document.querySelector("#timestamp")
  const error_origin = document.querySelector("#origin")

  error_timestamp.innerText = error_data.timestamp
  error_origin.innerText = error_data.origin

}

