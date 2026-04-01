// Servidor Express para servir o frontend estático no Render
// Este arquivo substitui o Vercel como host do frontend

const express = require('express')
const path = require('path')
const app = express()

const PORT = process.env.PORT || 3000

// Serve os arquivos estáticos do build do Vite
app.use(express.static(path.join(__dirname, 'dist')))

// Para qualquer rota não encontrada, retorna o index.html (SPA routing)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'))
})

app.listen(PORT, () => {
  console.log(`Frontend rodando na porta ${PORT}`)
})
