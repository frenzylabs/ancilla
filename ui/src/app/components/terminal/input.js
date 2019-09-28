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
  constructor(props) {
    super(props)

    this.state = {
      entry: ''
    }

    this.inputAction  = this.inputAction.bind(this)
    this.keyAction    = this.keyAction.bind(this)
  }

  componentDidMount(){
    document.addEventListener("keydown", this.keyAction, false)
  }
  componentWillUnmount(){
    document.removeEventListener("keydown", this.keyAction, false)
  }

  keyAction(e) {
    if(e.keyCode === 13 && this.state.entry.length > 0) { 
    

      $('#terminal-input').val('')
    }
  }

  inputAction(e) {
    const target = $(e.currentTarget)

    this.setState({
      ...this.state,
      entry: target.val()
    })
  }

  render() {
    return (
      <Form ref={(el) => this.formRef = el } size='tiny'>
        <Form.Input id="terminal-input" disabled={!this.props.connected} placeholder="Ender GCode" name="cmd" width={16} onChange={this.inputAction} />
      </Form>
    )
  }
}
