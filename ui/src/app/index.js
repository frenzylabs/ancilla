//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Grid
} from 'semantic-ui-react'

import {
  Connections,
  Terminal
} from './components'

export default class App extends React.Component {
  constructor(props) {
    super(props)

    this.renderMasterColumn = this.renderMasterColumn.bind(this)
    this.renderDetailColumn = this.renderDetailColumn.bind(this)
  }

  renderMasterColumn() {
    return (
      <Connections/>
    )
  }

  renderDetailColumn() {
    return (
      <Terminal/>
    )
  }

  render() {
    return (
      <Grid id="main-view" columns={2} celled style={{margin: 0, padding: 0, height: '100%', minHeight: '100%', maxHeight: '100%'}}>
        <Grid.Row>

          <Grid.Column id="master-column" style={{background: 'white', flex: '0 0 200px'}}>
            {this.renderMasterColumn()}
          </Grid.Column>

          <Grid.Column id="detail-column">
            {this.renderDetailColumn()}
          </Grid.Column>

        </Grid.Row>
      </Grid>
    )
  }
}
