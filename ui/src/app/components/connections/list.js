//
//  list.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React        from 'react'
import TextTruncate from 'react-text-truncate'

import {
  Menu,
  Header,
  Button
} from 'semantic-ui-react'

import {default as PrinterRequest}  from '../../network/printer'
import NewConnectionModal           from './new/modal'

export default class ConnectionList extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      printers: []
    }

    this.renderList = this.renderList.bind(this)
  }

  componentDidMount() {
    PrinterRequest.list()
    .then((res) => {
      this.setState({
        ...this.state,
        printers: res.data
      })
    })
    .catch((error) => {
      console.log("Error: ", error)
    })
  }

  renderList() {
    if(this.state.printers.length < 1) {
      return (
        <Button key="-1" style={{background: 'none', width: '100%', textAlign: 'left', padding:'0 0 0 0.5em'}} disabled>
          <TextTruncate line={1} truncateText="…" text="No connections." />
        </Button>
      )
    }

    return this.state.printers.map((item) => {
      return (
        <Button key={item.id} style={{background: 'none', width: '100%', textAlign: 'left', padding:'0 0 10px 0.5em'}}>
          <TextTruncate line={1} truncateText="…" text={item.name} />
        </Button>
      )
    })
  }

  render() {
    return (
      <Menu.Item>
          <Menu.Header>
            <Menu secondary compact>
              <Menu.Item position='left' style={{padding: 0}}>
                <Header textAlign='left' size='medium'>Connections</Header>
              </Menu.Item>
              
              <Menu.Menu position='right'>
                <Menu.Item>
                  <NewConnectionModal />
                </Menu.Item>
              </Menu.Menu>
            </Menu>
          </Menu.Header>
          
          <Menu.Item>
            {this.renderList()}
          </Menu.Item>
        </Menu.Item>
    )
  }
}
