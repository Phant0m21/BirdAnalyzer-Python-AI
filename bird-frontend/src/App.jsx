import { useState } from 'react'
import './App.css'

const API = 'http://localhost:8000'

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  function selectImage(event) {
    const selected = event.target.files[0]

    if (!selected) return

    if (!['image/jpeg', 'image/png'].includes(selected.type)) {
      setError('Выберите изображение')
      return
    }

    setFile(selected)
    setPreview(URL.createObjectURL(selected))
    setResult(null)
    setError('')
    setStatus('')
  }

  async function analyzeImage() {
    if (!file || loading) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API}/analyze`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail)
      }

      const task = await response.json()

      for (let i = 0; i < 300; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000))

        const resultResponse = await fetch(
          `${API}/result/${task.task_id}`
        )

        if (!resultResponse.ok) {
          throw new Error('Не удалось сделать анализ')
        }

        const data = await resultResponse.json()

        if (data.status === 'completed') {
          setResult(data.result)
          setStatus('')
          return
        }
      }

      throw new Error('Таймаут истек')
    } catch (err) {
      setError(err.message)
      setStatus('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <h1>Анализ птичек 🕊️</h1>

      <div className="upload">
        <input
          type="file"
          id="image"
          accept=".jpg,.jpeg,.png"
          onChange={selectImage}
          hidden
        />

        <label htmlFor="image" className="upload-button">
          Выбрать
        </label>

        {preview && (
          <img
            src={preview}
            className="preview"
          />
        )}

        {file && <p className="filename">{file.name}</p>}

        <button
          className="analyze-button"
          onClick={analyzeImage}
          disabled={!file || loading}
        >
          {loading ? 'Идет анализ' : 'Анализ'}
        </button>

        {status && <p className="status">{status}</p>}
        {error && <p className="error">{error}</p>}
      </div>

      {result && (
        <div className="result">
          <p>
            Вид птицы: {result.predicted_species}
          </p>

          <p>
            Уверенность: {result.confidence.toFixed(2)}%
          </p>

          <h4>Другие возможные варианты</h4>

          {result.predictions.map((item, index) => (
            <div className="prediction" key={index}>
              <span>{item.species}</span>
              <span>{item.confidence.toFixed(2)}%</span>
            </div>
          ))}

          <p className="description">{result.description}</p>
        </div>
      )}
    </div>
  )
}

export default App