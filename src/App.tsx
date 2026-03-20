import { RouterProvider } from 'react-router-dom'
import { AppProvider } from './stores'
import { router } from './router'
import './App.less'

function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  )
}

export default App
