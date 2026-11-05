
import { useState } from 'react'
import {
  View,
  Text,
  Image,
  Pressable,
  ScrollView,
  StyleSheet
} from 'react-native'
import * as ImagePicker from 'expo-image-picker'

const API = 'http://192.168.0.186:8000' // ☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️☝️

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  async function selectImage() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync()

    if (!permission.granted) return

    const selected = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1
    })

    if (selected.canceled) return

    const image = selected.assets[0]

    if (!['image/jpeg', 'image/png'].includes(image.mimeType)) {
      setError('Выберите изображение')
      return
    }

    setFile({
      uri: image.uri,
      name: image.fileName || 'image.jpg',
      type: image.mimeType
    })

    setPreview(image.uri)
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

      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.type
      })

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
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.app}
    >
      <Text style={styles.title}>Анализ птичек 🕊️</Text>

      <View style={styles.upload}>
        <Pressable
          onPress={selectImage}
          style={styles.uploadButton}
        >
          <Text style={styles.buttonText}>Выбрать</Text>
        </Pressable>

        {preview !== '' && (
          <Image
            source={{ uri: preview }}
            style={styles.preview}
            resizeMode="contain"
          />
        )}

        {file && (
          <Text style={styles.filename}>
            {file.name}
          </Text>
        )}

        <Pressable
          onPress={analyzeImage}
          disabled={!file || loading}
          style={styles.analyzeButton}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Идет анализ' : 'Анализ'}
          </Text>
        </Pressable>

        {status !== '' && (
          <Text style={styles.status}>{status}</Text>
        )}

        {error !== '' && (
          <Text style={styles.error}>{error}</Text>
        )}
      </View>

      {result && (
        <View style={styles.result}>
          <Text style={styles.resultText}>
            Вид птицы: {result.predicted_species}
          </Text>

          <Text style={styles.resultText}>
            Уверенность: {result.confidence.toFixed(2)}%
          </Text>

          <Text style={styles.resultHeading}>
            Другие возможные варианты
          </Text>

          {result.predictions.map((item, index) => (
            <View style={styles.prediction} key={index}>
              <Text style={styles.predictionText}>
                {item.species}
              </Text>

              <Text style={styles.predictionText}>
                {item.confidence.toFixed(2)}%
              </Text>
            </View>
          ))}

          <Text style={styles.description}>
            {result.description}
          </Text>
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f5f7fa'
  },
  app: {
    width: '100%',
    maxWidth: 600,
    alignSelf: 'center',
    marginTop: 60,
    padding: 30,
    alignItems: 'center'
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#222',
    textAlign: 'center'
  },
  upload: {
    width: '100%',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 18
  },
  uploadButton: {
    backgroundColor: '#0878d1',
    borderRadius: 6,
    paddingVertical: 7,
    paddingHorizontal: 48
  },
  analyzeButton: {
    backgroundColor: '#0878d1',
    borderRadius: 6,
    paddingVertical: 7,
    paddingHorizontal: 48
  },
  buttonText: {
    color: 'white',
    fontSize: 16
  },
  preview: {
    width: '100%',
    height: 300
  },
  filename: {
    color: '#555',
    textAlign: 'center'
  },
  status: {
    color: '#0878d1'
  },
  error: {
    color: '#d32f2f'
  },
  result: {
    width: '100%',
    marginTop: 35,
    padding: 25,
    alignItems: 'stretch',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8
  },
  resultText: {
    color: '#222',
    fontSize: 16,
    marginBottom: 10
  },
  resultHeading: {
    color: '#222',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 20,
    marginBottom: 10
  },
  prediction: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 15,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  predictionText: {
    color: '#222',
    fontSize: 14,
    flexShrink: 1
  },
  description: {
    color: '#222',
    marginTop: 20,
    fontSize: 14
  }
})

export default App
