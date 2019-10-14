//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React        from 'react'
import queryString  from 'query-string'
import {connect}    from 'react-redux'
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
      buffer:     []
    }

    this.trashAction  = this.trashAction.bind(this)
    this.onMessage    = this.onMessage.bind(this)
    this.powerAction  = this.powerAction.bind(this)
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

  componentDidMount() {
    if(this.state.connection) { 
      this.state.connection.disconnect()
    }

    const query     = queryString.parse(this.props.location.search)
    const name      = query.name
    const baudrate  = query.baudrate
    const path      = query.path

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

  componentWillUnmount() {
    if(!this.state.connection) { return }

    this.state.connection.disconnect()
  }
  powerAction() {
      if (this.state.connection) {
        if (this.state.connection.connected) {
          this.state.connection.connect()
        } else {
          this.state.connection.disconnect()
        }
      }
  }

  render() {
    return (
      <Segment.Group id="terminal">
        <Segment.Inline id="terminal-header">
          <TerminalHeader 
            connection={this.state.connection}
            trashAction={this.trashAction}
            powerAction={this.powerAction}
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
