//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/26/19
//  Copyright 2019 Wess Cope
//

import 'semantic-ui-css/semantic.min.css'
import './styles/app.scss'

import React    from "react"
import ReactDOM from "react-dom"
import App      from './app'

window.onload = () => {
  ReactDOM.render(
    <App />,
    document.getElementById('app')
  )
}
