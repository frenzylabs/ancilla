//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/26/19
//  Copyright 2019 Wess Cope
//

import 'semantic-ui-css/semantic.min.css'
import './styles/app.scss'

import React      from "react"
import ReactDOM   from "react-dom"
import {Provider} from 'react-redux'

import App        from './app'
import {printer}  from './app/network'
import store      from './app/store'

store.dispatch(printer.list())
store.dispatch(printer.ports())

window.onload = () => {
  ReactDOM.render(
    <Provider store={store}>
      <App />
      </Provider>,
    document.getElementById('app')
  )
}
