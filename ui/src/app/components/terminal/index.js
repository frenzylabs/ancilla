//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React        from 'react'
import queryString  from 'query-string'
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

    this.state = {
      connection: null,
      connected: false,
      buffer:     []
    }

    this.setupConnection  = this.setupConnection.bind(this)
    this.powerAction      = this.powerAction.bind(this)
    this.trashAction      = this.trashAction.bind(this)
    this.onMessage        = this.onMessage.bind(this)
  }

  componentDidMount() {
    this.setupConnection()
  }

  setupConnection() {
    const query     = queryString.parse(this.props.location.search)
    const name      = query.name
    const baudrate  = query.baudrate
    const path      = query.path

    const conn = providers.connection.get({
      name:     name,
      path:     path,
      baudrate: baudrate
    })

    conn.onMessageHandler = this.onMessage

    this.setState({
      connection: conn,
      buffer:     this.state.buffer.concat(conn.buffer)
    })
  }

  powerAction(e) {
    if(this.state.connection == null) { this.setupConnection() }

    if(this.state.connected) {
      this.state.connection.disconnect()
    } else {
      this.state.connection.connect()
    }
    

    this.setState({
      connected: !this.state.connected
    })
  }

  trashAction(e) {
    this.setState({
      buffer: []
    })
  }
  
  onMessage(msg) {
    this.setState({
      buffer: this.state.buffer.concat([msg])
    })
  }

  render() {
    return (
      <Segment.Group id="terminal">
        <Segment.Inline id="terminal-header">
          <TerminalHeader 
            connected={this.state.connected}
            connection={this.state.connection}
            powerAction={this.powerAction}
            trashAction={this.trashAction}
          />
        </Segment.Inline>

        <Segment.Inline id='terminal-body'>
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
