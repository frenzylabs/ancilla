//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import { 
  Table, 
  Segment
} from 'semantic-ui-react'

import TerminalHeader from './header'
import TerminalBody   from './body'
import TerminalInput  from './input'

export default class Terminal extends React.Component {
  constructor(props) {
    super(props)
  }

  render() {
    return (
      <Segment.Group id="terminal">
        <Segment.Inline id="terminal-header">
          <TerminalHeader/>
        </Segment.Inline>

        <Segment.Inline id='terminal-body'>
          <Table singleLine inverted>
            <TerminalBody />
          </Table>
        </Segment.Inline>

        <Segment compact inverted id="terminal-input">
          <TerminalInput />
        </Segment>

      </Segment.Group>
    )
  }
}
