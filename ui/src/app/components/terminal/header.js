//
//  header.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'

import { 
  Button, 
  Icon, 
  Menu
} from 'semantic-ui-react'

export default class TerminalHeader extends React.Component {
  constructor(props) {
    super(props)

    this.powerAction  = this.powerAction.bind(this)
    this.cogAction    = this.cogAction.bind(this)
    this.trashAction  = this.trashAction.bind(this)
  }
  
  powerAction(e) {
    if(this.props.powerAction) {
      this.props.powerAction(e)
    }
  }

  cogAction(e) {
    if(this.props.cogAction) {
      this.props.cogAction(e)
    }
  }

  trashAction(e) {
    console.log("Trash")
  }

  render() {
    return(
      <Menu borderless={true} fluid size='tiny' compact inverted style={{border: 'none', borderRadius: '0'}}>
        <Menu.Item header>
            Connection:
        </Menu.Item>

        <Menu.Item>
          None &nbsp;
        </Menu.Item>

        <Menu.Item>
          /example/path/here
        </Menu.Item>

        <Menu.Menu position="right">
          <Button.Group size='small'>
            <Button disabled={!this.props.connected} icon style={{background: 'none', color: '#fff'}} onClick={this.powerAction}><Icon name='power' /></Button>
            <Button disabled={!this.props.connected} icon style={{background: 'none', color: '#fff'}} onClick={this.cogAction}><Icon name='cog' /></Button>
            <Button disabled={!this.props.connected} icon style={{background: 'none', color: '#fff'}} onClick={this.trashAction}><Icon name='trash alternate outline' /></Button>
          </Button.Group>
        </Menu.Menu>
      </Menu>
    )
  }
}
