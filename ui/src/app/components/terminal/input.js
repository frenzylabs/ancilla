//
//  input.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React  from 'react'
import $      from 'jquery/dist/jquery'

import { 
  Form, 
} from 'semantic-ui-react'

export default class TerminalInput extends React.Component {
  historyIndex    = 0
  trackingHistory = false

  constructor(props) {
    super(props)

    this.state = {
      history: [],
      entry: ''
    }

    this.sendAction     = this.sendAction.bind(this)
    this.enterAction    = this.enterAction.bind(this)
    this.upAction       = this.upAction.bind(this)
    this.downAction     = this.downAction.bind(this)
    this.setInputValue  = this.setInputValue.bind(this)
    this.inputAction    = this.inputAction.bind(this)
    this.keyAction      = this.keyAction.bind(this)
  }

  componentDidMount(){
    document.addEventListener("keydown", this.keyAction, false)
  }
  componentWillUnmount(){
    document.removeEventListener("keydown", this.keyAction, false)
  }

  sendAction() {
    (this.state.entry.includes('&&') ? this.state.entry.split('&&') : [this.state.entry]).map((item) => {
      return JSON.stringify({
        action: 'command',
        code: item.trim()
      })
    }).forEach(this.props.connection.send)
  }

  enterAction() {
    if(this.state.entry.length < 1) { return }

    var history = (this.state.history || [])
    history.unshift(this.state.entry)

    this.setState({
      history: history
    })
  
    this.sendAction()

    this.historyIndex = 0
    $('#terminal-input-field').val('')

  }

  upAction() {
    if(this.historyIndex >= this.state.history.length) { 
      return 
    }

    let line = this.state.history[this.historyIndex]

    this.historyIndex += 1

    this.setInputValue(line)
  }

  downAction() {
    this.historyIndex -= 1

    var line = ""

    if(this.historyIndex < 0) {
      this.historyIndex = 0
    } else {
      line = this.state.history[this.historyIndex]
    }

    this.setInputValue(line)
}

  setInputValue(value) {
    $('#terminal-input-field').focus()
    $('#terminal-input-field').val('')
    
    setTimeout(function() {
      $('#terminal-input-field').val(value)
    }, 1)

  }
  
  keyAction(e) {
    switch(e.keyCode) {
      case 13: { // Enter
        this.enterAction()
        return
      }

      case 38: { // Up
        this.upAction()
        return
      }

      case 40: { // Down
        this.downAction()
        return
      }

      default: 
        return
    }

    console.log("keycode: ", e.keyCode)

  }

  inputAction(e) {
    const target = $(e.currentTarget)

    this.setState({
      entry: target.val()
    })

    target.val(target.val())
  }

  render() {
    return (
      <Form ref={(el) => this.formRef = el } size='tiny'>
        <Form.Input 
          id="terminal-input-field" 
          disabled={!this.props.connection} 
          placeholder="Enter command or GCode" 
          name="cmd" 
          width={16} 
          onChange={this.inputAction} 
        />
      </Form>
    )
  }
}
