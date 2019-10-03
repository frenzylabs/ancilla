//
//  header.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'

import { 
  Button, 
  Icon, 
  Menu
} from 'semantic-ui-react'

import {notification} from '../../store/actions'

class TerminalHeader extends React.Component {
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

    this.props.dispatch(notification.info("Hello World"))
  }

  render() {
    return(
      <Menu borderless={true} fluid size='tiny' compact inverted style={{border: 'none', borderRadius: '0'}}>
        <Menu.Item header>
            Connection: &nbsp;

            {this.props.connection && (this.props.connection.name != this.props.connection.path) && 
                <span>{this.props.connection.name}</span>
            }

        </Menu.Item>

        { this.props.connection && 
            <Menu.Item>              
              {this.props.connection.path}
            </Menu.Item>
        }

        <Menu.Menu position="right">
          <Button.Group size='small'>
            <Button disabled={!this.props.connected} icon style={{background: 'none', color: '#fff'}} onClick={this.powerAction}><Icon name='power' /></Button>
            <Button disabled={!this.props.connected} icon style={{background: 'none', color: '#fff'}} onClick={this.cogAction}><Icon name='cog' /></Button>
            <Button icon style={{background: 'none', color: '#fff'}} onClick={this.trashAction}><Icon name='trash alternate outline' /></Button>
          </Button.Group>
        </Menu.Menu>
      </Menu>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    connection: state.connection.currentConnection
  }
}

export default connect(mapStateToProps)(TerminalHeader)
