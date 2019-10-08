//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'

import {Connection} from '../../network'

import { 
  Table, 
  Segment
} from 'semantic-ui-react'

import TerminalHeader from './header'
import TerminalBody   from './body'
import TerminalInput  from './input'

class Terminal extends React.Component {
  constructor(props) {
    super(props)

    console.log("mount")

    this.state = {
      connection: null,
      buffer:     []
    }

    this.onMessage = this.onMessage.bind(this)
  }

  onMessage(msg) {
    this.setState({
      buffer: this.state.buffer.concat([msg])
    })
  }

  componentDidMount() {
    if(this.state.connection) { return }

    const name      = this.props.location.connectionProps.name
    const baudrate  = this.props.location.connectionProps.baudrate
    const path      = this.props.location.connectionProps.path

    const conn      = new Connection({
      name:     name,
      path:     path,
      baudrate: baudrate
    })

    conn.onMessageHandler = this.onMessage

    conn.connect()

    this.setState({
      connection: conn
    })
  }

  render() {
    console.log("Rendering terminal")
    
    return (
      <Segment.Group id="terminal">
        <Segment.Inline id="terminal-header">
          <TerminalHeader connection={this.state.connection}/>
        </Segment.Inline>

        <Segment.Inline id='terminal-body' style={{overflow: 'hidden'}}>
          <TerminalBody buffer={this.state.buffer}/>
        </Segment.Inline>

        <Segment.Inline id="terminal-input">
          <TerminalInput connection={this.state.connection}/>
        </Segment.Inline>

      </Segment.Group>
    )
  }
}

export default Terminal
